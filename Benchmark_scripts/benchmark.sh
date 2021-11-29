logFileName="utilization-logs.csv"
#calculate the remaining time to queue the next log api call precisely
function waitToNextMinute {
   currentTime=$(date +%s)
   seconds=$(($(date +%s)%60)) #get seconds of current time
   timeToSleep=$((60-$seconds))
   sleep $timeToSleep
}
coreCount=$(kubectl describe nodes | sed -n '/Capacity:/,/ephemeral-storage:/{//!p;}'  | awk '{print $2}')
echo "CPU Cores: $coreCount"

echo logging cluster info
start_time=$(date +%s)
end_time=$(date +%s)
elapsed=$(( end_time - start_time ))
echo $(date)
echo "waiting for clear minute"
echo "Date,CPUMili,CPUPercent,CpuPercentPrecise,MemoryBytesUsage,MemoryPercentUsage"
calc() { awk "BEGIN{print $*}"; }

waitToNextMinute
while [ $elapsed -lt 86400 ]
do
   logTimeStamp=$(date +"%T")
   kubePerformanceOutput=$(kubectl top nodes --use-protocol-buffers)
   logCPUMili=$(echo $kubePerformanceOutput | cut -d" " -f7)
   logCPUPercent=$(echo $kubePerformanceOutput | cut -d" " -f8)
   CPUMiliNumber=$(echo $kubePerformanceOutput | cut -d" " -f7 | sed 's/.$//')
   logCpuPercentPrecise=$(calc $(calc $CPUMiliNumber/$coreCount)/10)
   logMemoryUsageBytes=$(echo $kubePerformanceOutput | cut -d" " -f9)
   logMemoryUsagePercent=$(echo $kubePerformanceOutput | cut -d" " -f10)
   logLine=$logTimeStamp,$logCPUMili,$logCPUPercent,$logCpuPercentPrecise,$logMemoryUsageBytes,$logMemoryUsagePercent
   echo $logLine >> $logFileName
   echo $logLine
   elapsed=$(( end_time - start_time ))
   waitToNextMinute
done