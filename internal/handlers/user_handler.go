package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"df-backpack/internal/models"
	"df-backpack/internal/websocket"
)

type UserHandler struct {
	wsManager *websocket.Manager
	users     map[string]*models.User
}

func NewUserHandler(wsManager *websocket.Manager) *UserHandler {
	return &UserHandler{
		wsManager: wsManager,
		users:     make(map[string]*models.User),
	}
}

func (h *UserHandler) GetUsers(w http.ResponseWriter, r *http.Request) {
	users := make([]*models.User, 0, len(h.users))
	for _, user := range h.users {
		users = append(users, user)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(users)
}

func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
	var user models.User
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	user.ID = generateID()
	user.CreatedAt = time.Now()
	h.users[user.ID] = &user

	// Broadcast ke WebSocket clients
	message := map[string]interface{}{
		"type": "user_created",
		"data": user,
	}
	messageBytes, _ := json.Marshal(message)
	h.wsManager.BroadcastMessage(messageBytes)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(user)
}

func (h *UserHandler) SendMessage(w http.ResponseWriter, r *http.Request) {
	var message struct {
		Content string `json:"content"`
		UserID  string `json:"user_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&message); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	msg := models.Message{
		ID:        generateID(),
		UserID:    message.UserID,
		Content:   message.Content,
		Timestamp: time.Now(),
	}

	// Broadcast message ke WebSocket clients
	wsMessage := map[string]interface{}{
		"type": "new_message",
		"data": msg,
	}
	messageBytes, _ := json.Marshal(wsMessage)
	h.wsManager.BroadcastMessage(messageBytes)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(msg)
}

func generateID() string {
	return time.Now().Format("20060102150405")
}
