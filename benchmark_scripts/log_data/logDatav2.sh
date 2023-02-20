logFileName="utilization-logs.csv"
#set certain time for benchmark start
targetTime="today 9:59" #can also be tomorrow/today with time or simply now for immediate start
echo "$(date) sleeping until: $targetTime"
sleep $(( $(date -f - +%s- <<< "$targetTime"$'\nnow') 0 ))

#calculate the remaining time to queue the next log api call precisely
function waitToNextMinute {
   currentTime=$(date +%s)
   seconds=$(($(date +%s)%60)) #get seconds of current time
   timeToSleep=$((60-$seconds))
   sleep $timeToSleep
}
coreCount=$(kubectl describe nodes | sed -n '/Capacity:/,/ephemeral-storage:/{//!p;}'  | awk '{print $2}' | sed '1q;d') # modified for two nodes
echo "CPU Cores: $coreCount"

echo logging cluster info
start_time=$(date +%s)
end_time=$(date +%s)
elapsed=$(( end_time - start_time ))
echo $(date)
echo "waiting for clear minute"
echo "Date,CPUMili,CPUPercent,CpuPercentPrecise,MemoryBytesUsage,MemoryPercentUsage"
calc() { awk "BEGIN{print $*}";}

# waitToNextMinute  #not needed since time trigger is used now
while [ $elapsed -lt 86400 ]
do
   logTimeStamp=$(date +"%a %T")
   #get logs from kubectl API
   kubePerformanceOutput=$(kubectl top nodes --use-protocol-buffers)
   kubeReservationOutput=$(kubectl describe nodes | sed -n '/Allocated resources:/,/Events:/{//!p;}' | sed '4q;d')
   kubeReservationOutput2=$(kubectl describe nodes | sed -n '/Allocated resources:/,/Events:/{//!p;}' | sed '11q;d')
   kubeSLAOutput=$(kubectl get pods -l realtime=critical --field-selector=status.phase=Pending --namespace=pod-benchmark | wc -l) #SLA Check
   #filtering block of the results

   #filtering cpuRealtimeData
   logCPUMili=$(echo $kubePerformanceOutput | cut -d" " -f7)
   logCPUMili2=$(echo $kubePerformanceOutput | cut -d" " -f12)
   logCPUPercent=$(echo $kubePerformanceOutput | cut -d" " -f8)
   logCPUPercent2=$(echo $kubePerformanceOutput | cut -d" " -f13)
   CPUMiliNumber=$(echo $kubePerformanceOutput | cut -d" " -f7 | sed 's/.$//')
   CPUMiliNumber2=$(echo $kubePerformanceOutput | cut -d" " -f12 | sed 's/.$//')
   logCpuPercentPrecise=$(calc $(calc $CPUMiliNumber/$coreCount)/10)
   logCpuPercentPrecise2=$(calc $(calc $CPUMiliNumber2/$coreCount)/10)

   #filtering cpuReservations
   logcpuMiliReservation=$(echo $kubeReservationOutput | awk '{print $2}' | sed 's/.$//')
   logcpuMiliReservation2=$(echo $kubeReservationOutput2 | awk '{print $2}' | sed 's/.$//')
   logcpuPercentReservation=$(echo $kubeReservationOutput | awk '{print $3}' | cut -c 2- | sed 's/.\{2\}$//')
   logcpuPercentReservation2=$(echo $kubeReservationOutput2 | awk '{print $3}' | cut -c 2- | sed 's/.\{2\}$//')
   logcpuPreciseReservation=$(calc $(calc $logcpuMiliReservation/$coreCount)/10)
   logcpuPreciseReservation2=$(calc $(calc $logcpuMiliReservation2/$coreCount)/10)

   logLine=$logTimeStamp,$logCPUMili,$logCPUPercent,$logCpuPercentPrecise,$logcpuMiliReservation,$logcpuPercentReservation,$logcpuPreciseReservation,$logCPUMili2,$logCPUPercent2,$logCpuPercentPrecise2,$logcpuMiliReservation2,$logcpuPercentReservation2,$logcpuPreciseReservation2,$kubeSLAOutput
   echo $logLine >> $logFileName
   echo $logLine
   
   sleep 5
   echo "cleaning of old deployments"
   kubectl delete pod --field-selector=status.phase==Succeeded --namespace pod-benchmark #delete completed pods
   
   elapsed=$(( end_time - start_time ))
   waitToNextMinute
done