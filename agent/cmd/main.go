package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type RequestMetrics struct {
	TotalRequests   int64
	UniqueIPs       map[string]bool
	SuspiciousCount int64
	ErrorsCount     int64
	TotalPayload    int64
	mu              sync.RWMutex
}

type AggregatedWindow struct {
	AgentID            string  `json:"agent_id"`
	WindowStart        string  `json:"window_start"`
	WindowEnd          string  `json:"window_end"`
	TotalRequests      int     `json:"total_requests"`
	UniqueIPs          int     `json:"unique_ips"`
	UniqueIPsRatio     float64 `json:"unique_ips_ratio"`
	SuspiciousRequests int     `json:"suspicious_requests"`
	SuspiciousRatio    float64 `json:"suspicious_ua_ratio"`
	ErrorsCount        int     `json:"errors_count"`
	ErrorRate          float64 `json:"error_rate"`
	AvgPayloadSize     int     `json:"avg_payload_size"`
}

type RuleUpdate struct {
	BlockIPs  []string `json:"block_ips"`
	RateLimit int      `json:"rate_limit_rps"`
	UpdatedAt string   `json:"updated_at"`
}

var (
	metrics    = &RequestMetrics{UniqueIPs: make(map[string]bool)}
	localRules struct {
		sync.RWMutex
		BlockedIPs map[string]bool
		RateLimit  int
	}
	agentID   string
	serverURL string
)

func init() {
	localRules.BlockedIPs = make(map[string]bool)
	localRules.RateLimit = 100
	agentID = os.Getenv("AGENT_ID")
	if agentID == "" {
		agentID = fmt.Sprintf("agent-%d", time.Now().UnixNano()%100000)
	}
	serverURL = os.Getenv("SERVER_URL")
	if serverURL == "" {
		serverURL = "http://backend:8000"
	}
}

func startRulePoller() {
	ticker := time.NewTicker(1 * time.Second)
	go func() {
		for range ticker.C {
			func() {
				resp, err := http.Get(serverURL + "/api/v1/agent/rules")
				if err != nil {
					return // Тихо игнорируем ошибки сети до запуска бэкенда
				}
				defer resp.Body.Close()
				
				if resp.StatusCode != 200 {
					return
				}
				
				var newRules RuleUpdate
				if err := json.NewDecoder(resp.Body).Decode(&newRules); err == nil {
					localRules.Lock()
					
					// Проверяем, действительно ли правила изменились
					rulesChanged := false
					if len(newRules.BlockIPs) != len(localRules.BlockedIPs) {
						rulesChanged = true
					} else {
						for _, ip := range newRules.BlockIPs {
							if !localRules.BlockedIPs[ip] {
								rulesChanged = true
								break
							}
						}
					}

					if rulesChanged {
						localRules.BlockedIPs = make(map[string]bool)
						for _, ip := range newRules.BlockIPs {
							localRules.BlockedIPs[ip] = true
						}
						localRules.RateLimit = newRules.RateLimit
						localRules.Unlock()
						log.Printf("SUCCESS: Agent rules updated! Now actively blocking %d IPs.", len(localRules.BlockedIPs))
					} else {
						localRules.Unlock()
					}
				}
			}()
		}
	}()
}

func startMetricsAggregator() {
	ticker := time.NewTicker(30 * time.Second)
	go func() {
		for range ticker.C {
			sendAggregatedMetrics()
		}
	}()
}

func sendAggregatedMetrics() {
	metrics.mu.Lock()
	snapshot := RequestMetrics{
		TotalRequests:   atomic.LoadInt64(&metrics.TotalRequests),
		UniqueIPs:       make(map[string]bool),
		SuspiciousCount: atomic.LoadInt64(&metrics.SuspiciousCount),
		ErrorsCount:     atomic.LoadInt64(&metrics.ErrorsCount),
		TotalPayload:    atomic.LoadInt64(&metrics.TotalPayload),
	}
	for ip := range metrics.UniqueIPs {
		snapshot.UniqueIPs[ip] = true
	}
	atomic.StoreInt64(&metrics.TotalRequests, 0)
	atomic.StoreInt64(&metrics.SuspiciousCount, 0)
	atomic.StoreInt64(&metrics.ErrorsCount, 0)
	atomic.StoreInt64(&metrics.TotalPayload, 0)
	metrics.UniqueIPs = make(map[string]bool)
	metrics.mu.Unlock()
	
	if snapshot.TotalRequests == 0 {
		return
	}
	
	uniqueCount := len(snapshot.UniqueIPs)
	uniqueRatio := float64(uniqueCount) / float64(snapshot.TotalRequests)
	suspiciousRatio := float64(snapshot.SuspiciousCount) / float64(snapshot.TotalRequests)
	errorRate := float64(snapshot.ErrorsCount) / float64(snapshot.TotalRequests)
	avgPayload := int(snapshot.TotalPayload / snapshot.TotalRequests)
	
	window := AggregatedWindow{
		AgentID:            agentID,
		WindowStart:        time.Now().Add(-30 * time.Second).UTC().Format(time.RFC3339),
		WindowEnd:          time.Now().UTC().Format(time.RFC3339),
		TotalRequests:      int(snapshot.TotalRequests),
		UniqueIPs:          uniqueCount,
		UniqueIPsRatio:     uniqueRatio,
		SuspiciousRequests: int(snapshot.SuspiciousCount),
		SuspiciousRatio:    suspiciousRatio,
		ErrorsCount:        int(snapshot.ErrorsCount),
		ErrorRate:          errorRate,
		AvgPayloadSize:     avgPayload,
	}
	
	data, _ := json.Marshal([]AggregatedWindow{window})
	resp, err := http.Post(
		serverURL+"/api/v1/agent/metrics",
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		log.Printf("Error: failed to send metrics: %v", err)
		return
	}
	defer resp.Body.Close()
	log.Printf("Metrics sent: %d requests, %d unique IPs", window.TotalRequests, uniqueCount)
}

func isSuspiciousUserAgent(ua string) bool {
	ua = strings.ToLower(ua)
	suspiciousPatterns := []string{
		"bot", "crawler", "spider", "scraper", "wget", "curl",
		"python-requests", "go-http-client", "java/", "libwww",
	}
	for _, p := range suspiciousPatterns {
		if strings.Contains(ua, p) {
			return true
		}
	}
	return ua == ""
}

func extractClientIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		return strings.TrimSpace(parts[0])
	}
	if xri := r.Header.Get("X-Real-IP"); xri != "" {
		return xri
	}
	parts := strings.Split(r.RemoteAddr, ":")
	if len(parts) > 0 {
		return parts[0]
	}
	return r.RemoteAddr
}

func handler(w http.ResponseWriter, r *http.Request) {
	clientIP := extractClientIP(r)
	
	localRules.RLock()
	if localRules.BlockedIPs[clientIP] {
		localRules.RUnlock()
		w.WriteHeader(http.StatusForbidden)
		fmt.Fprintf(w, "Blocked by Net Protector: IP in blacklist")
		return
	}
	localRules.RUnlock()
	
	ua := r.UserAgent()
	isSuspicious := isSuspiciousUserAgent(ua)
	
	atomic.AddInt64(&metrics.TotalRequests, 1)
	atomic.AddInt64(&metrics.TotalPayload, int64(r.ContentLength))
	if isSuspicious {
		atomic.AddInt64(&metrics.SuspiciousCount, 1)
	}
	
	metrics.mu.Lock()
	metrics.UniqueIPs[clientIP] = true
	metrics.mu.Unlock()
	
	w.Header().Set("X-Protected-By", "Net Protector")
	w.Header().Set("X-Agent-ID", agentID)
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"protected","agent":"%s","ip":"%s","suspicious":%v}`, agentID, clientIP, isSuspicious)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	localRules.RLock()
	blockedCount := len(localRules.BlockedIPs)
	rateLimit := localRules.RateLimit
	localRules.RUnlock()
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"agent_id":         agentID,
		"status":           "active",
		"blocked_ips":      blockedCount,
		"rate_limit":       rateLimit,
		"total_requests":   atomic.LoadInt64(&metrics.TotalRequests),
		"suspicious_count": atomic.LoadInt64(&metrics.SuspiciousCount),
	})
}

func main() {
	log.Printf("Net Protector Agent started")
	log.Printf("Agent ID: %s", agentID)
	log.Printf("Server URL: %s", serverURL)
	
	startRulePoller()
	startMetricsAggregator()
	
	http.HandleFunc("/", handler)
	http.HandleFunc("/agent/health", healthHandler)
	
	log.Println("Agent listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}