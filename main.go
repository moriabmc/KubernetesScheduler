package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/comail/colog"
	"github.com/julienschmidt/httprouter"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/types"
	schedulerapi "k8s.io/kubernetes/pkg/scheduler/apis/extender/v1"
)

const (
	versionPath      = "/version"
	apiPrefix        = "/scheduler"
	bindPath         = apiPrefix + "/bind"
	preemptionPath   = apiPrefix + "/preemption"
	predicatesPrefix = apiPrefix + "/predicates"
	prioritiesPrefix = apiPrefix + "/priorities"
)

var pods map[string]float64
var workload_sum float64

var unoptimized bool = false // set true to disable Temporal shifting

var lastPodTimeStamp int64 = 0

var workload_data_prediction []float64
var runtime_data_prediction []float64

// Set these parameters according to your cluster
var VERBOSE = false                                   // extra logging
var id map[string]int = map[string]int{"minikube": 0} // maps name to id
var UNCERTAINTY float64 = 0.05                        // defines the uncertainty of the limit
var NODES int = 1                                     // defines the number of nodes in the cluster
var HOURS int = 24                                    // defines the size of the scheduling window
var MAX float64 = 4000                                // max millicores per Node
var STATIC []float64 = []float64{850}                 // static millicores per Node

var START_HOUR int = 5                    // will be set to current time of deployment plus 1, dont deploy earlier than 1 hour in advance!
var shifted_workload [][]float64          // shifted workload per Node per hour
var shifted_workload_critical [][]float64 // shifted critical workload per Node per hour
var optimal_window [][]float64            // optimal window per Node
var co2_rank_values []int
var co2_rank_nodes []int
var co2_data_float [][]float64      // predicted co2 emissions per Node
var real_co2_data_float [][]float64 // real co2 emissions per Node

var (
	version string // injected via ldflags at build time

	TruePredicate = Predicate{
		Name: "always_true",
		Func: func(pod v1.Pod, node v1.Node) (bool, error) {
			return true, nil
		},
	}

	//generate host priority list and set all of them to default value zero
	ZeroPriority = Prioritize{
		Name: "zero_score",
		Func: func(_ v1.Pod, nodes []v1.Node) (*schedulerapi.HostPriorityList, error) {
			var priorityList schedulerapi.HostPriorityList
			priorityList = make([]schedulerapi.HostPriority, len(nodes))
			log.Print("Prioritize is called!")
			for i, node := range nodes {
				priorityList[i] = schedulerapi.HostPriority{
					Host:  node.Name,
					Score: 1,
				}
			}
			return &priorityList, nil
		},
	}

	Co2Priority = Prioritize{
		Name: "zero_score", // name must be zero_score
		Func: func(_ v1.Pod, nodes []v1.Node) (*schedulerapi.HostPriorityList, error) {
			var priorityList schedulerapi.HostPriorityList
			priorityList = make([]schedulerapi.HostPriority, len(nodes))
			var hour_utc_plus_one = (time.Now().Hour() + 1) % 24
			location := getPrefferedLocation(hour_utc_plus_one)
			log.Print("Preffered Location ", location)
			for i, node := range nodes {
				var score int64 = 0
				if node.Labels["location"] == strconv.Itoa(location) {
					log.Print("Optimal Node: ", node.Name)
					score = 100
				}
				priorityList[i] = schedulerapi.HostPriority{
					Host:  node.Name,
					Score: score,
				}
			}
			return &priorityList, nil
		},
	}

	NoBind = Bind{
		Func: func(podName string, podNamespace string, podUID types.UID, node string) error {
			return fmt.Errorf("this extender doesn't support bind.  please make 'BindVerb' be empty in your ExtenderConfig.")
		},
	}

	EchoPreemption = Preemption{
		Func: func(
			_ v1.Pod,
			_ map[string]*schedulerapi.Victims,
			nodeNameToMetaVictims map[string]*schedulerapi.MetaVictims,
		) map[string]*schedulerapi.MetaVictims {
			return nodeNameToMetaVictims
		},
	}
)

func StringToLevel(levelStr string) colog.Level {
	switch level := strings.ToUpper(levelStr); level {
	case "TRACE":
		return colog.LTrace
	case "DEBUG":
		return colog.LDebug
	case "INFO":
		return colog.LInfo
	case "WARNING":
		return colog.LWarning
	case "ERROR":
		return colog.LError
	case "ALERT":
		return colog.LAlert
	default:
		log.Printf("warning: LOG_LEVEL=\"%s\" is empty or invalid, fallling back to \"INFO\".\n", level)
		return colog.LInfo
	}
}

func main() {
	colog.SetDefaultLevel(colog.LInfo)
	colog.SetMinLevel(colog.LInfo)
	colog.SetFormatter(&colog.StdFormatter{
		Colors: true,
		Flag:   log.Ldate | log.Ltime | log.Lshortfile,
	})
	colog.Register()
	level := StringToLevel(os.Getenv("INFO"))
	log.Print("Log level was set to ", strings.ToUpper(level.String()))
	START_HOUR = (time.Now().Hour() + 2) % 24 //must be +2 for productive run
	log.Print("Start hour was set to ", START_HOUR)
	log.Print("initialize lookup tables:")
	initialize_lookup_tables()
	log.Print("finished initializing lookup tables:")
	colog.SetMinLevel(level)
	getCPUUtilization(NODES)
	router := httprouter.New()
	AddVersion(router)

	predicates := []Predicate{TruePredicate}
	for _, p := range predicates {
		AddPredicate(router, p)
	}

	priorities := []Prioritize{} // remove to disable Co2Priority
	for _, p := range priorities {
		AddPrioritize(router, p)
	}

	AddBind(router, NoBind)

	log.Print("info: server starting on the port :80")
	if err := http.ListenAndServe(":80", router); err != nil {
		log.Fatal(err)
	}
}

// simple function to read in a csv file as a 2d list
func readCsvFile(filePath string) [][]string {
	f, err := os.Open(filePath)
	if err != nil {
		log.Fatal("Unable to read input file "+filePath, err)
	}
	defer f.Close()

	csvReader := csv.NewReader(f)
	records, err := csvReader.ReadAll()
	if err != nil {
		log.Fatal("Unable to parse file as CSV for "+filePath, err)
	}
	return records
}

func read_workload_prediction(filePath string) []float64 {
	log.Print("reading workload file")
	workload_data := readCsvFile(filePath)
	workload_data_float := make([]float64, len(workload_data))
	for i := 0; i < len(workload_data); i++ {
		workload_data_float[i], _ = strconv.ParseFloat(workload_data[i][0], 64)
	}
	return workload_data_float
}

// external function call for main, to trigger the csv parsing on startup of the scheduler (only performed once)
func initialize_lookup_tables() {
	co2_data := make([][][]string, NODES)
	real_co2_data := make([][][]string, NODES)
	co2_data_float = make([][]float64, NODES)
	real_co2_data_float = make([][]float64, NODES)

	for i := 0; i < NODES; i++ {
		predicted := "../usr/bin/co2_prediction.csv"
		real := "../usr/bin/co2_emission.csv"
		if i > 0 {
			predicted = fmt.Sprint("../usr/bin/co2_prediction", i+1, ".csv")
			real = fmt.Sprint("../usr/bin/co2_emission", i+1, ".csv")
		}
		co2_data[i] = readCsvFile(predicted)
		real_co2_data[i] = readCsvFile(real)
	}

	for j := 0; j < NODES; j++ {
		co2_data_float[j] = make([]float64, HOURS)
		real_co2_data_float[j] = make([]float64, HOURS)
		for i := 0; i < HOURS; i++ {
			co2_data_float[j][i], _ = strconv.ParseFloat(co2_data[j][i][0], 64)
			real_co2_data_float[j][i], _ = strconv.ParseFloat(real_co2_data[j][i][0], 64)
		}
	}

	for i := 0; i < NODES; i++ {
		log.Print("Node ", i)
		log.Print("CO2 Prediction:", co2_data_float[i])
		log.Print("Real CO2:", real_co2_data_float[i])
	}

	runtime_data := readCsvFile("../usr/bin/runtime_prediction.csv")
	runtime_data_prediction = make([]float64, len(runtime_data))
	for i := 0; i < len(runtime_data); i++ {
		runtime_data_prediction[i], _ = strconv.ParseFloat(runtime_data[i][0], 64)
	}
	log.Print("Runtime Prediction: ", runtime_data_prediction)

	workload_data_prediction = read_workload_prediction("../usr/bin/workload_prediction.csv")
	log.Print("Workload Prediction: ", workload_data_prediction)

	co2_rank_nodes, co2_rank_values = rank(co2_data_float)

	shifted_workload = make([][]float64, NODES)
	shifted_workload_critical = make([][]float64, NODES)
	for i := 0; i < NODES; i++ {
		shifted_workload[i] = make([]float64, HOURS)
		shifted_workload_critical[i] = make([]float64, HOURS)
	}

	pods = make(map[string]float64)
	workload_sum = 0
	optimal_window = calculate_optimal_window()
}

// This method extracts CPU limits out of the kubernetes server kubectl api
func getCPUUtilization(nodeCount int) (map[string]float64, error) {
	//block to aquire values
	var cpuLimits map[string]float64 = make(map[string]float64, NODES)
	cmd := exec.Command("kubectl", "describe", "nodes")
	stdout, err := cmd.Output()
	//catch in case the api gets unresponsive some time.
	if err != nil {
		return nil, err //default to 100 percent usage, esentially blocking until service comes up again
	}
	//create regex that gets the cpu line
	//regex that does not work because of instruction set :(
	//Allocated resources:(.|\n)*cpu(\s)*(\d)*m(\s)*\(\K(\d)*
	cpuLimits_str := make([]string, nodeCount)
	getCpu := regexp.MustCompile("cpu(\\s)*(\\d)*m(\\s)*\\((\\d)*")
	getName := regexp.MustCompile("Name:(\\s)*(\\w|-)*")
	cpuResultConsole := getCpu.FindAllStringSubmatch(string(stdout), nodeCount)
	nameResult := getName.FindAllStringSubmatch(string(stdout), nodeCount)
	//extract the percentage value of the cpu utilization
	for i := 0; i < nodeCount; i++ {
		name := strings.TrimSpace(nameResult[i][0])[20:]
		cpuLimits_str[i] = cpuResultConsole[i][0][(strings.IndexByte(cpuResultConsole[i][0], '(') + 1):]
		x, _ := strconv.ParseFloat(cpuLimits_str[i], 64)
		cpuLimits[name] = x / 100
	}
	log.Print("cpu limits: ", cpuLimits)
	return cpuLimits, nil
}

// returns a 2d float array representing the cpu limits for each node and hour
func calculate_optimal_window() [][]float64 {
	log.Print("--------- Calculate Optimal Window ---------")
	optimal_workload := make([][]float64, NODES)
	for node := 0; node < NODES; node++ {
		optimal_workload[node] = make([]float64, HOURS)
	}

	queue := workload_sum / (3600 * MAX)
	current_hour := int((time.Now().Hour() + 1) % 24)
	i := 0
	for queue > 0 {
		log.Print("i ", i)
		log.Print("Queue ", queue)
		// calculate the dynamic limit for the current optimal hour for both nodes
		log.Print("Prediction ", workload_data_prediction[co2_rank_values[i]])
		log.Print("Shifted Workload Critical ", shifted_workload_critical[co2_rank_nodes[i]][co2_rank_values[i]]/(3600*MAX))
		log.Print("Shifted Workload ", shifted_workload[co2_rank_nodes[i]][co2_rank_values[i]]/(3600*MAX))
		limit := 1 - workload_data_prediction[co2_rank_values[i]] + shifted_workload_critical[co2_rank_nodes[i]][co2_rank_values[i]]/(3600*MAX) - UNCERTAINTY
		log.Print("Limit ", limit)
		// prevent index out of bound at last hour
		if i+1 > HOURS*NODES {
			log.Print("Index Out of Bound, schedule immediately")
			for node := 0; node < NODES; node++ {
				optimal_workload[node][current_hour] = 1 // schedule all workload immediately
			}
			break
		}
		// check if the optimal co2 hour has already past, if so check next most optimal hour
		if ((co2_rank_values[i] < current_hour) && (current_hour < START_HOUR)) ||
			((current_hour < START_HOUR) && (START_HOUR < co2_rank_values[i])) ||
			((START_HOUR < co2_rank_values[i]) && (co2_rank_values[i] < current_hour)) {
			log.Print("Optimal hour has already past")
			i++
			continue
		}
		// IF: check if queue can be scheduled entirely, ELSE: set optimal workload to current limit and subtract scheduled workload from queue
		if (STATIC[co2_rank_nodes[i]]/MAX)+(shifted_workload[co2_rank_nodes[i]][co2_rank_values[i]]/(3600*MAX))+queue < limit {
			optimal_workload[co2_rank_nodes[i]][co2_rank_values[i]] = STATIC[co2_rank_nodes[i]]/MAX + shifted_workload[co2_rank_nodes[i]][co2_rank_values[i]]/(3600*MAX) + queue
			queue = 0
		} else {
			optimal_workload[co2_rank_nodes[i]][co2_rank_values[i]] = limit
			queue = queue + STATIC[co2_rank_nodes[i]]/MAX + shifted_workload[co2_rank_nodes[i]][co2_rank_values[i]]/(3600*MAX) - limit
		}
		i++
	}
	for node := 0; node < NODES; node++ {
		log.Print("Optimal Workload Node ", node+1, ":", optimal_workload[node])
	}
	return optimal_workload
}

/*
Backup, no dynamic limits

	func calculate_optimal_window() []float64 {
		optimal_workload := make([]float64, 24)
		queue := workload_sum / (3600 * 4000)
		log.Print("Pods in queue:", len(pods))
		log.Print("Total Workload: ", queue)
		current_hour := int((time.Now().Hour() + 1) % 24)
		log.Print("Start hour ", START_HOUR)
		log.Print("Current hour ", current_hour)
		i := 0
		limit := 0.9
		for queue > 0 {

			log.Print("Co2 hour ", co2_rank[i])
			if i > 23 {
				log.Print("Cannot Shape Workload efficiently")
				optimal_workload[current_hour] = limit
				break
			}
			if ((co2_rank[i] < current_hour) && (current_hour < START_HOUR)) || ((current_hour < START_HOUR) && (START_HOUR < co2_rank[i])) || ((START_HOUR < co2_rank[i]) && (co2_rank[i] < current_hour)) { //Expression can probably be reduced
				log.Print("Co2 hour out of range")
				i++
				continue
			}
			if workload_data_prediction[co2_rank[i]]+(shifted_workload[co2_rank[i]]/(3600*4000))+queue < limit {
				optimal_workload[co2_rank[i]] = workload_data_prediction[co2_rank[i]] + (shifted_workload[co2_rank[i]] / (3600 * 4000)) + queue
				queue = 0
			} else {
				optimal_workload[co2_rank[i]] = limit
				queue = queue + workload_data_prediction[co2_rank[i]] + (shifted_workload[co2_rank[i]] / (3600 * 4000)) - limit
			}
			i++
		}
		return optimal_workload
	}
*/

// Returns the sorted indexes of a 2d float array
func rank(emission [][]float64) ([]int, []int) {
	var values []int
	var nodes []int

	for i := 0; i < HOURS*NODES; i++ {
		min := 0
		node := 0
		for n := 0; n < NODES; n++ {
			for h := 0; h < HOURS; h++ {
				if emission[n][h] < emission[node][min] {
					node = n
					min = h
				}
			}
		}
		values = append(values, min)
		nodes = append(nodes, node)
		emission[node][min] = 9999
	}
	return nodes, values
}

// returns the index of the location with minimal co2 grid emission using historical data
func getPrefferedLocation(hour_utc_plus_one int) int {
	prefferedNode := 0
	for node := 0; node < NODES; node++ {
		if real_co2_data_float[node][hour_utc_plus_one] < real_co2_data_float[prefferedNode][hour_utc_plus_one] {
			prefferedNode = node
		}
	}
	return prefferedNode
}
