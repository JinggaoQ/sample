# HttpServer in AWS Nitro Enclave
![image](https://github.com/JinggaoQ/sample/blob/master/enclave_httpserver/enclave_httpserver.png)

1.Create Docker Image

docker build ./ -t enclave_httpserver

2.Package the Enclave EIF

nitro-cli build-enclave --docker-uri enclave_httpserver:latest --output-file httptest.eif

3.Run Enclave

nitro-cli run-enclave --cpu-count 2 --memory 6144 --eif-path httptest.eif --debug-mode

4.Monitoring the Enclave console

ENCLAVE_ID=$(nitro-cli describe-enclaves | jq -r ".[0].EnclaveID")
nitro-cli console --enclave-id ${ENCLAVE_ID}

5.Open another Terminal in Parent Instance, replace the vsock CID 16 in following command.

docker run -p 8001:8001 alpine/socat TCP-LISTEN:8001,fork,reuseaddr VSOCK-CONNECT:16:8001

6.Run Client App

curl http://127.0.0.1 8001

7.Console output

Hello, Enclave Http server!


