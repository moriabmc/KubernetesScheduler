package main

import (
	"log"
	"time"

	v1 "k8s.io/api/core/v1"
	schedulerapi "k8s.io/kubernetes/pkg/scheduler/apis/extender/v1"
)

type Predicate struct {
	Name string
	Func func(pod v1.Pod, node v1.Node) (bool, error)
}

func (p Predicate) Handler(args schedulerapi.ExtenderArgs) *schedulerapi.ExtenderFilterResult {

	pod := args.Pod
	canSchedule := make([]v1.Node, 0, len(args.Nodes.Items))
	canNotSchedule := make(map[string]string)

	// Turn optimization off
	if unoptimized {
		for _, node := range args.Nodes.Items {
			result, err := p.Func(*pod, node)
			if err != nil {
				canNotSchedule[node.Name] = err.Error()
			} else {
				if result {
					canSchedule = append(canSchedule, node)
				}
			}
		}

		result := schedulerapi.ExtenderFilterResult{
			Nodes: &v1.NodeList{
				Items: canSchedule,
			},
			FailedNodes: canNotSchedule,
			Error:       "",
		}

		return &result
	}

	// Implementation of the scheduler
	for _, node := range args.Nodes.Items {
		result, err := p.Func(*pod, node)

		//Block to assign server state variables
		cpulimits, err := getCPUUtilization(NODES)
		var cpulimit float64
		if err != nil {
			//TODO handle error
			cpulimit = 1
		} else {
			cpulimit = cpulimits[node.Name]
		}
		podMilliCores := pod.Spec.Containers[0].Resources.Requests.Cpu().MilliValue()
		if VERBOSE {
			log.Print("---------- Start of Log Print ----------")

			log.Print("---------- Get Metadata of pod ----------")

			log.Print("Get Result (boolean): ", result)

			log.Print("---------- Get timestamp of pod ----------")
			log.Print("Get pod unix timestamp: ", pod.GetCreationTimestamp().Unix(), "curent time is: ", time.Now().Unix())
			log.Print("Get pod hour: ", pod.GetCreationTimestamp().Hour())
			log.Print("Get pod minute: ", pod.GetCreationTimestamp().Minute())
			log.Print("Get pod seconds: ", pod.GetCreationTimestamp().Second())
			log.Print("Get Pod resource requests: ", podMilliCores)
			log.Print("cpu Limit of nodes as float is: ", cpulimit)

			log.Print("---------- End of Scheduler Log print ----------")
		}

		var labels = pod.GetLabels()
		log.Print("Printing label value: ", labels["realtime"]) //printing whether critical pod or not for debugging purposes

		var hour_utc_plus_one = (time.Now().Hour() + 1) % 24
		log.Print("current hour utc+1 adapted is: ", hour_utc_plus_one) //used on code level, as changing container time zone did not work

		var podage = time.Now().Unix() - pod.GetCreationTimestamp().Unix()

		var maximum_shift_time = int64(86400) // 24 hours, after this a pod is basically treated as a critical pod
		log.Print("Current pod waiting for: ", podage, " seconds")
		log.Print("Pod priority class is: ", pod.Spec.PriorityClassName)

		nodeID := id[node.Name]

		if err != nil {
			canNotSchedule[node.Name] = err.Error()
		} else {
			if result {
				if (pod.Spec.PriorityClassName == "not-critical") && (podage < maximum_shift_time) && (cpulimit > optimal_window[nodeID][hour_utc_plus_one]) {
					if pod.GetCreationTimestamp().Unix() > lastPodTimeStamp {
						log.Print("New not-critical Pod enqueued")
						pods[pod.GetName()] = float64(podMilliCores) * runtime_data_prediction[hour_utc_plus_one]
						workload_sum = workload_sum + float64(podMilliCores)*runtime_data_prediction[hour_utc_plus_one]
						optimal_window = calculate_optimal_window()
					} else {
						log.Print("Pod is already in queue")
					}
				} else {
					nodeID := id[node.Name]
					if pod.Spec.PriorityClassName == "not-critical" {
						log.Print("Not-Critical Pod has been scheduled")
						pod_cpu := pods[pod.GetName()] // get scheduled pod resource usage
						if pod_cpu == 0 {              // If pod is not in queue we increase the shifted workload
							optimal_window = calculate_optimal_window()
							shifted_workload_critical[nodeID][hour_utc_plus_one] = shifted_workload_critical[nodeID][hour_utc_plus_one] + float64(podMilliCores)*runtime_data_prediction[hour_utc_plus_one]
						} else {
							shifted_workload[nodeID][hour_utc_plus_one] = shifted_workload[nodeID][hour_utc_plus_one] + pod_cpu
							workload_sum = workload_sum - pod_cpu
						}
					} else if pod.Spec.PriorityClassName == "critical" { // If pod is critical we increase the shifted workload critical
						shifted_workload_critical[nodeID][hour_utc_plus_one] = shifted_workload_critical[nodeID][hour_utc_plus_one] + float64(podMilliCores)*runtime_data_prediction[hour_utc_plus_one]
					}
					log.Print("can schedule!")
					canSchedule = append(canSchedule, node)
				}
			}
		}
		if pod.GetCreationTimestamp().Unix() > lastPodTimeStamp {
			lastPodTimeStamp = pod.GetCreationTimestamp().Unix()
		}
	}

	result := schedulerapi.ExtenderFilterResult{
		Nodes: &v1.NodeList{
			Items: canSchedule,
		},
		FailedNodes: canNotSchedule,
		Error:       "",
	}

	return &result
}
