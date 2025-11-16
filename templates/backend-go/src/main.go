package main

import (
    "fmt"
    "log"
    "net/http"
)

func healthHandler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprint(w, `{"status":"ok"}`)
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", healthHandler)

    addr := ":8080"
    log.Printf("Starting Go API on %s", addr)
    if err := http.ListenAndServe(addr, mux); err != nil {
        log.Fatalf("server error: %v", err)
    }
}
