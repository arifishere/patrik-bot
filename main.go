package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/ollama/ollama/api"
)

const (
	// defaultModel is the custom Ollama model built from ./Modelfile (FROM gemma4:e2b).
	defaultModel   = "patrik"
	defaultBaseURL = "http://localhost:11434"
	defaultAddr    = ":7860"
)

func ollamaModel() string {
	if model := os.Getenv("OLLAMA_MODEL"); model != "" {
		return model
	}
	return defaultModel
}

func ollamaBaseURL() string {
	if baseURL := os.Getenv("OLLAMA_BASE_URL"); baseURL != "" {
		return baseURL
	}
	return defaultBaseURL
}

func listenAddr() string {
	if addr := os.Getenv("ADDR"); addr != "" {
		return addr
	}
	return defaultAddr
}

func newOllamaClient(baseURL string) (*api.Client, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		return nil, fmt.Errorf("parse ollama base url: %w", err)
	}
	return api.NewClient(u, http.DefaultClient), nil
}

func chatRequest(model, userMessage string) *api.ChatRequest {
	think := &api.ThinkValue{Value: false}
	stream := true
	// Persona lives in the Ollama Modelfile SYSTEM prompt for model "patrik".
	return &api.ChatRequest{
		Model:  model,
		Stream: &stream,
		Think:  think,
		Messages: []api.Message{
			{Role: "user", Content: userMessage},
		},
	}
}

type emitFunc func(chunk string)

func streamChat(ctx context.Context, client *api.Client, model, userMessage string, emit emitFunc) error {
	return client.Chat(ctx, chatRequest(model, userMessage), func(resp api.ChatResponse) error {
		if resp.Message.Content != "" {
			emit(resp.Message.Content)
		}
		return nil
	})
}

type chatRequestBody struct {
	Message string `json:"message"`
}

func chatHandler(client *api.Client, model string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var body chatRequestBody
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, "invalid json body", http.StatusBadRequest)
			return
		}
		message := strings.TrimSpace(body.Message)
		if message == "" {
			http.Error(w, "message is required", http.StatusBadRequest)
			return
		}

		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "streaming unsupported", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")

		writeSSE := func(payload string) {
			_, _ = fmt.Fprintf(w, "data: %s\n\n", payload)
			flusher.Flush()
		}

		err := streamChat(r.Context(), client, model, message, func(chunk string) {
			encoded, encErr := json.Marshal(chunk)
			if encErr != nil {
				return
			}
			writeSSE(string(encoded))
		})
		if err != nil {
			writeSSE("[ERROR] " + err.Error())
			return
		}
		writeSSE("[DONE]")
	}
}

func main() {
	model := ollamaModel()
	baseURL := ollamaBaseURL()
	addr := listenAddr()

	client, err := newOllamaClient(baseURL)
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()
	mux.Handle("/", http.FileServer(http.Dir("web")))
	mux.HandleFunc("/api/chat", chatHandler(client, model))

	server := &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
	}()

	log.Printf("Patrik bot → Ollama (%s @ %s) at http://localhost%s", model, baseURL, addr)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
