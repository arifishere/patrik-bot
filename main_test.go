package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestOllamaModel_Default(t *testing.T) {
	t.Setenv("OLLAMA_MODEL", "")
	require.Equal(t, defaultModel, ollamaModel())
}

func TestOllamaModel_FromEnv(t *testing.T) {
	t.Setenv("OLLAMA_MODEL", "gemma3:1b")
	require.Equal(t, "gemma3:1b", ollamaModel())
}

func TestOllamaBaseURL_Default(t *testing.T) {
	t.Setenv("OLLAMA_BASE_URL", "")
	require.Equal(t, defaultBaseURL, ollamaBaseURL())
}

func TestOllamaBaseURL_FromEnv(t *testing.T) {
	t.Setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
	require.Equal(t, "http://127.0.0.1:11434", ollamaBaseURL())
}

func TestChatRequest_UserMessageOnly(t *testing.T) {
	req := chatRequest("patrik", "Hello")

	require.Equal(t, "patrik", req.Model)
	require.NotNil(t, req.Stream)
	require.True(t, *req.Stream)
	require.NotNil(t, req.Think)
	require.Equal(t, false, req.Think.Value)
	require.Len(t, req.Messages, 1)
	require.Equal(t, "user", req.Messages[0].Role)
	require.Equal(t, "Hello", req.Messages[0].Content)
}

func TestNewOllamaClient_InvalidURL(t *testing.T) {
	_, err := newOllamaClient("://bad")
	require.Error(t, err)
}

func TestChatHandler_MethodNotAllowed(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/api/chat", nil)
	rec := httptest.NewRecorder()

	chatHandler(nil, defaultModel)(rec, req)

	require.Equal(t, http.StatusMethodNotAllowed, rec.Code)
}

func TestChatHandler_EmptyMessage(t *testing.T) {
	body, err := json.Marshal(chatRequestBody{Message: "   "})
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodPost, "/api/chat", strings.NewReader(string(body)))
	rec := httptest.NewRecorder()

	chatHandler(nil, defaultModel)(rec, req)

	require.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestChatHandler_InvalidJSON(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/api/chat", strings.NewReader("{"))
	rec := httptest.NewRecorder()

	chatHandler(nil, defaultModel)(rec, req)

	require.Equal(t, http.StatusBadRequest, rec.Code)
}
