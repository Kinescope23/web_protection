package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	serverURL := os.Getenv("SERVER_URL")
	if serverURL == "" {
		serverURL = "http://localhost:8000"
	}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprintf(w, `<!DOCTYPE html>
<html>
<head><title>Net Protector Agent</title></head>
<body style="font-family: Arial; background: #f5f5f5; padding: 40px;">
  <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <h1 style="color: #667eea;">Net Protector Agent</h1>
    <p>Агент защиты запущен и готов к работе.</p>
    <p><strong>Центральный сервер:</strong> %s</p>
    <p><strong>Статус:</strong> Активен</p>
    <hr>
    <p style="color: #888; font-size: 0.9em;">Версия 0.1.0 • Этап 1</p>
  </div>
</body>
</html>`, serverURL)
	})

	log.Println("Net Protector Agent запущен на :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}