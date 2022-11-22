![image](https://github.com/JinggaoQ/sample/blob/master/enclave_httpserver/enclave_httpserver.png)

创建Docker Image
docker build ./ -t enclave_httpserver

打包Enclave EIF
nitro-cli build-enclave --docker-uri enclave_httpserver:latest --output-file httptest.eif

运行Enclave
nitro-cli run-enclave --cpu-count 2 --memory 6144 --eif-path httptest.eif --debug-mode

观察Enclave console输出
ENCLAVE_ID=$(nitro-cli describe-enclaves | jq -r ".[0].EnclaveID")
nitro-cli console --enclave-id ${ENCLAVE_ID}

打开另外一个Terminal, 在Parent Instance客户端，替换vsocke的CID 16为当前实际的数值
docker run -p 8001:8001 alpine/socat TCP-LISTEN:8001,fork,reuseaddr VSOCK-CONNECT:16:8001

运行Client App
curl http://127.0.0.1 8001
Hello, Enclave Http server!


