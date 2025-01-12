FROM golang:1.13-alpine as builder
ARG VERSION=0.0.1

ENV GO111MODULE=on
ENV CGO_ENABLED=0
ENV GOOS=linux
ENV GOARCH=amd64



# build
WORKDIR /go/src/k8s-scheduler-extender-example
COPY go.mod .
COPY go.sum .
RUN GO111MODULE=on go mod download
COPY . .
RUN go install -ldflags "-s -w -X main.version=$VERSION" k8s-scheduler-extender-example

# runtime image
FROM gcr.io/google_containers/hyperkube:v1.16.3
# Image is stored from directory to container directory
COPY --from=builder /go/bin/k8s-scheduler-extender-example /usr/bin/k8s-scheduler-extender-example
#Integrate File with co2 prediction data
COPY ./co2_prediction/co2_prediction.csv /usr/bin/co2_prediction.csv
COPY ./co2_prediction/co2_prediction2.csv /usr/bin/co2_prediction2.csv
COPY ./co2_prediction/co2_emission.csv /usr/bin/co2_emission.csv
COPY ./co2_prediction/co2_emission2.csv /usr/bin/co2_emission2.csv

#COPY ./co2_prediction/average_co2_emissions_loc2.csv /usr/bin/average_co2_emissions_loc2.csv
#Integrate workload prediction data
COPY ./benchmark_scripts/workload_generator/workload_prediction.csv /usr/bin/workload_prediction.csv
#Integrate runtime prediction data
COPY ./benchmark_scripts/workload_generator/runtime_prediction.csv /usr/bin/runtime_prediction.csv

ENTRYPOINT ["k8s-scheduler-extender-example"]
