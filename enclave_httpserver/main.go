package main

import (
	"io"
	"log"
	"net/http"
)

const PORT = ":8888"

func main() {
	handler := func(w http.ResponseWriter, req *http.Request) {
		io.WriteString(w, "Hello, Enclave Http server!\\n")
	}

	http.HandleFunc("/", handler)
	log.Println("listening on", PORT)
	log.Fatal(http.ListenAndServe(PORT, nil))
}
