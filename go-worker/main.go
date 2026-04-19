package main

import (
	"encoding/json"
	"errors"
	"log/slog"
	"math"
	"math/rand"
	"net/http"
	"os"
	"time"
)

type solveRequest struct {
	Method  string      `json:"method"`
	Matrix  [][]float64 `json:"matrix"`
	MaxTime float64     `json:"max_time"`
}

type solveResponse struct {
	Tour          []int   `json:"tour"`
	Cost          float64 `json:"cost"`
	Method        string  `json:"method"`
	ExecutionTime float64 `json:"execution_time"`
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "healthy", "service": "go-tsp-worker"})
	})
	mux.HandleFunc("/solve", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req solveRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		if req.Method != "Random" && req.Method != "HC" {
			writeError(w, http.StatusBadRequest, "unsupported method")
			return
		}

		n := len(req.Matrix)
		if err := validateMatrix(req.Matrix); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}

		maxTime := req.MaxTime
		if maxTime <= 0 {
			maxTime = 1.0
		}

		start := time.Now()
		rng := rand.New(rand.NewSource(time.Now().UnixNano()))

		var tour []int
		if req.Method == "Random" {
			tour = randomTour(n, rng)
		} else {
			tour = hillClimb(req.Matrix, maxTime, rng)
		}

		resp := solveResponse{
			Tour:          tour,
			Cost:          tourCost(req.Matrix, tour),
			Method:        req.Method,
			ExecutionTime: time.Since(start).Seconds(),
		}

		writeJSON(w, http.StatusOK, resp)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	logger.Info("starting go worker", "port", port)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		logger.Error("server stopped", "error", err)
		os.Exit(1)
	}
}

func validateMatrix(matrix [][]float64) error {
	if len(matrix) == 0 {
		return errors.New("matrix cannot be empty")
	}
	n := len(matrix)
	for _, row := range matrix {
		if len(row) != n {
			return errors.New("matrix must be square")
		}
	}
	return nil
}

func randomTour(n int, rng *rand.Rand) []int {
	tour := make([]int, n)
	for i := 0; i < n; i++ {
		tour[i] = i
	}
	rng.Shuffle(n, func(i, j int) {
		tour[i], tour[j] = tour[j], tour[i]
	})
	return tour
}

func hillClimb(matrix [][]float64, maxTime float64, rng *rand.Rand) []int {
	n := len(matrix)
	if n < 2 {
		return randomTour(n, rng)
	}
	best := randomTour(n, rng)
	bestCost := tourCost(matrix, best)

	deadline := time.Now().Add(time.Duration(maxTime * float64(time.Second)))
	if maxTime <= 0.02 {
		deadline = time.Now().Add(20 * time.Millisecond)
	}

	for time.Now().Before(deadline) {
		candidate := append([]int(nil), best...)
		i := rng.Intn(n)
		j := rng.Intn(n)
		if i == j {
			continue
		}
		candidate[i], candidate[j] = candidate[j], candidate[i]
		candidateCost := tourCost(matrix, candidate)
		if candidateCost < bestCost {
			best = candidate
			bestCost = candidateCost
		}
	}

	return best
}

func tourCost(matrix [][]float64, tour []int) float64 {
	n := len(tour)
	if n == 0 {
		return 0
	}

	total := 0.0
	for i := 0; i < n; i++ {
		a := tour[i]
		b := tour[(i+1)%n]
		total += matrix[a][b]
	}

	if math.IsNaN(total) || math.IsInf(total, 0) {
		return math.MaxFloat64
	}

	return total
}

func writeError(w http.ResponseWriter, code int, detail string) {
	writeJSON(w, code, map[string]string{"detail": detail})
}

func writeJSON(w http.ResponseWriter, code int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(payload)
}
