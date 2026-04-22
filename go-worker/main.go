package main

import (
	"encoding/json"
	"errors"
	"log/slog"
	"math"
	"math/rand"
	"net/http"
	"os"
	"sort"
	"strings"
	"time"
)

type solveRequest struct {
	Method         string      `json:"method"`
	Matrix         [][]float64 `json:"matrix"`
	MaxTime        float64     `json:"max_time"`
	PopulationSize int         `json:"population_size"`
	Mutate         *bool       `json:"mutate"`
	SimulationType string      `json:"simulation_type"`
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
	allowedMethods := readAllowedMethodsFromEnv()
	isMethodAllowed := func(method string) bool {
		_, ok := allowedMethods[method]
		return ok
	}

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

		if !isMethodAllowed(req.Method) {
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
		switch req.Method {
		case "Random":
			tour = randomTour(n, rng)
		case "HC":
			tour = hillClimb(req.Matrix, maxTime, rng)
		case "Genetic":
			populationSize := req.PopulationSize
			if populationSize <= 0 {
				populationSize = 50
			}
			mutate := true
			if req.Mutate != nil {
				mutate = *req.Mutate
			}
			tour = geneticSolve(req.Matrix, maxTime, populationSize, mutate, rng)
		case "MCTS":
			simType := req.SimulationType
			if simType == "" {
				simType = "nearest"
			}
			tour = mctsSolve(req.Matrix, maxTime, simType, rng)
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
	logger.Info("allowed methods", "methods", mapKeys(allowedMethods))
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		logger.Error("server stopped", "error", err)
		os.Exit(1)
	}
}

func mapKeys(values map[string]struct{}) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func readAllowedMethodsFromEnv() map[string]struct{} {
	all := map[string]struct{}{
		"Random":  {},
		"HC":      {},
		"Genetic": {},
		"MCTS":    {},
	}

	raw := strings.TrimSpace(os.Getenv("ALLOWED_METHODS"))
	if raw == "" {
		return all
	}

	parsed := make(map[string]struct{})
	for _, part := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(part)
		if candidate == "" {
			continue
		}
		if _, ok := all[candidate]; ok {
			parsed[candidate] = struct{}{}
		}
	}

	if len(parsed) == 0 {
		return all
	}

	return parsed
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

func twoOptSwap(tour []int, i, j int) []int {
	swapped := append([]int(nil), tour...)
	for i < j {
		swapped[i], swapped[j] = swapped[j], swapped[i]
		i++
		j--
	}
	return swapped
}

func localMutateHillClimb(matrix [][]float64, tour []int, maxTime float64, rng *rand.Rand) []int {
	n := len(tour)
	if n < 2 {
		return append([]int(nil), tour...)
	}

	best := append([]int(nil), tour...)
	bestCost := tourCost(matrix, best)
	deadline := time.Now().Add(time.Duration(maxTime * float64(time.Second)))
	if maxTime <= 0.01 {
		deadline = time.Now().Add(10 * time.Millisecond)
	}

	for time.Now().Before(deadline) {
		i := rng.Intn(n)
		j := rng.Intn(n)
		if i == j {
			continue
		}
		if i > j {
			i, j = j, i
		}
		candidate := twoOptSwap(best, i, j)
		candidateCost := tourCost(matrix, candidate)
		if candidateCost < bestCost {
			best = candidate
			bestCost = candidateCost
		}
	}

	return best
}

func crossover(parentA, parentB []int, rng *rand.Rand) ([]int, []int) {
	n := len(parentA)
	if n < 2 {
		return append([]int(nil), parentA...), append([]int(nil), parentB...)
	}

	start := rng.Intn(n)
	span := int(math.Max(1, math.Floor(float64(n)*0.25)))
	limit := int(math.Max(float64(span), math.Floor(float64(n)*0.75)))
	h := span
	if limit > span {
		h = span + rng.Intn(limit-span+1)
	}

	buildChild := func(primary, secondary []int) []int {
		child := make([]int, 0, n)
		chosen := make(map[int]struct{}, n)
		for i := 0; i < h; i++ {
			v := secondary[(start+i)%n]
			child = append(child, v)
			chosen[v] = struct{}{}
		}
		for _, v := range primary {
			if _, exists := chosen[v]; !exists {
				child = append(child, v)
			}
		}
		return child
	}

	return buildChild(parentA, parentB), buildChild(parentB, parentA)
}

func geneticSolve(matrix [][]float64, maxTime float64, populationSize int, mutate bool, rng *rand.Rand) []int {
	n := len(matrix)
	if n < 2 {
		return randomTour(n, rng)
	}

	if populationSize < 2 {
		populationSize = 2
	}

	type individual struct {
		tour []int
		cost float64
	}

	population := make([]individual, 0, populationSize)
	for i := 0; i < populationSize; i++ {
		tour := randomTour(n, rng)
		population = append(population, individual{tour: tour, cost: tourCost(matrix, tour)})
	}

	sort.Slice(population, func(i, j int) bool {
		return population[i].cost < population[j].cost
	})
	best := append([]int(nil), population[0].tour...)
	bestCost := population[0].cost

	deadline := time.Now().Add(time.Duration(maxTime * float64(time.Second)))
	if maxTime <= 0.02 {
		deadline = time.Now().Add(20 * time.Millisecond)
	}

	for time.Now().Before(deadline) {
		rng.Shuffle(len(population), func(i, j int) {
			population[i], population[j] = population[j], population[i]
		})

		nextGen := make([]individual, 0, len(population))
		for i := 0; i+1 < len(population); i += 2 {
			c1, c2 := crossover(population[i].tour, population[i+1].tour, rng)
			nextGen = append(nextGen, individual{tour: c1, cost: tourCost(matrix, c1)})
			nextGen = append(nextGen, individual{tour: c2, cost: tourCost(matrix, c2)})
			if time.Now().After(deadline) {
				break
			}
		}

		if mutate {
			remaining := deadline.Sub(time.Now()).Seconds()
			if remaining <= 0 {
				break
			}
			perIndividual := math.Min(remaining/math.Max(float64(len(nextGen)), 1), 0.2)
			for i := range nextGen {
				nextGen[i].tour = localMutateHillClimb(matrix, nextGen[i].tour, perIndividual, rng)
				nextGen[i].cost = tourCost(matrix, nextGen[i].tour)
			}
		}

		population = append(population, nextGen...)
		sort.Slice(population, func(i, j int) bool {
			return population[i].cost < population[j].cost
		})
		if len(population) > populationSize {
			population = population[:populationSize]
		}

		if len(population) > 0 && population[0].cost < bestCost {
			bestCost = population[0].cost
			best = append([]int(nil), population[0].tour...)
		}
	}

	return best
}

type mctsNode struct {
	parent   *mctsNode
	tour     []int
	children []*mctsNode
	visited  bool
	mean     float64
	visits   int
}

func (n *mctsNode) isTerminal(size int) bool {
	return len(n.tour) == size
}

func (n *mctsNode) isLeaf() bool {
	return len(n.children) == 0
}

func containsNode(tour []int, node int) bool {
	for _, x := range tour {
		if x == node {
			return true
		}
	}
	return false
}

func (n *mctsNode) findChildren(size int) []*mctsNode {
	children := make([]*mctsNode, 0, size-len(n.tour))
	for candidate := 0; candidate < size; candidate++ {
		if containsNode(n.tour, candidate) {
			continue
		}
		childTour := append(append([]int(nil), n.tour...), candidate)
		children = append(children, &mctsNode{parent: n, tour: childTour})
	}
	return children
}

func (n *mctsNode) randomChild(matrix [][]float64, lottery string, rng *rand.Rand) *mctsNode {
	size := len(matrix)
	available := make([]int, 0, size-len(n.tour))
	for candidate := 0; candidate < size; candidate++ {
		if !containsNode(n.tour, candidate) {
			available = append(available, candidate)
		}
	}
	if len(available) == 0 {
		return n
	}

	choose := available[rng.Intn(len(available))]
	if lottery == "nearest" && len(n.tour) > 0 {
		last := n.tour[len(n.tour)-1]
		bestNode := available[0]
		bestWeight := matrix[last][bestNode]
		for _, v := range available[1:] {
			if matrix[last][v] < bestWeight {
				bestWeight = matrix[last][v]
				bestNode = v
			}
		}
		choose = bestNode
	}

	if lottery == "nearest lottery" && len(n.tour) > 0 {
		last := n.tour[len(n.tour)-1]
		weights := make([]float64, len(available))
		total := 0.0
		for i, v := range available {
			w := matrix[last][v]
			if w <= 0 {
				w = 1e-6
			}
			weights[i] = 1.0 / w
			total += weights[i]
		}
		target := rng.Float64() * total
		acc := 0.0
		for i, weight := range weights {
			acc += weight
			if acc >= target {
				choose = available[i]
				break
			}
		}
	}

	childTour := append(append([]int(nil), n.tour...), choose)
	return &mctsNode{parent: n, tour: childTour}
}

func (n *mctsNode) utc(allVisits int, exploreScale float64) float64 {
	if !n.visited || n.visits == 0 {
		return 0
	}
	return n.mean - exploreScale*math.Sqrt(math.Log2(math.Max(float64(allVisits), 2))/float64(n.visits))
}

func (n *mctsNode) update(cost float64) {
	n.mean = n.mean * float64(n.visits)
	n.visits++
	n.mean = (n.mean + cost) / float64(n.visits)
}

func chooseChild(node *mctsNode, iteration int) *mctsNode {
	if len(node.children) == 0 {
		return node
	}
	best := node.children[0]
	bestValue := best.utc(iteration, 2)
	for _, child := range node.children[1:] {
		value := child.utc(iteration, 2)
		if value < bestValue {
			best = child
			bestValue = value
		}
	}
	return best
}

func traverse(node *mctsNode, iteration int) *mctsNode {
	if node.isLeaf() {
		return node
	}
	return traverse(chooseChild(node, iteration), iteration)
}

func backpropagate(node *mctsNode, cost float64) {
	if node == nil || node.parent == nil {
		return
	}
	node.update(cost)
	backpropagate(node.parent, cost)
}

func simulate(node *mctsNode, matrix [][]float64, lottery string, rng *rand.Rand, bestTour *[]int, bestCost *float64) float64 {
	if node.isTerminal(len(matrix)) {
		cost := tourCost(matrix, node.tour)
		if cost < *bestCost {
			*bestCost = cost
			*bestTour = append([]int(nil), node.tour...)
		}
		return cost
	}
	return simulate(node.randomChild(matrix, lottery, rng), matrix, lottery, rng, bestTour, bestCost)
}

func mctsSolve(matrix [][]float64, maxTime float64, lottery string, rng *rand.Rand) []int {
	size := len(matrix)
	if size < 2 {
		return randomTour(size, rng)
	}

	root := &mctsNode{tour: []int{}, visited: true}
	bestTour := randomTour(size, rng)
	bestCost := tourCost(matrix, bestTour)
	iteration := 0

	deadline := time.Now().Add(time.Duration(maxTime * float64(time.Second)))
	if maxTime <= 0.02 {
		deadline = time.Now().Add(20 * time.Millisecond)
	}

	for time.Now().Before(deadline) {
		iteration++
		leaf := traverse(root, iteration)
		if leaf.isTerminal(size) {
			cost := tourCost(matrix, leaf.tour)
			if cost < bestCost {
				bestCost = cost
				bestTour = append([]int(nil), leaf.tour...)
			}
			backpropagate(leaf, cost)
			continue
		}

		if leaf.visited {
			leaf.children = leaf.findChildren(size)
			if len(leaf.children) > 0 {
				leaf = leaf.children[rng.Intn(len(leaf.children))]
			}
		} else {
			leaf.visited = true
		}

		cost := simulate(leaf, matrix, lottery, rng, &bestTour, &bestCost)
		backpropagate(leaf, cost)
	}

	return bestTour
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
