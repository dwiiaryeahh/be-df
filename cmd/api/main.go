package main

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/rs/cors"

	"df-backpack/internal/udp"
	"df-backpack/internal/websocket"
)

func main() {
	// Initialize WebSocket manager
	wsManager := websocket.NewManager()
	go wsManager.Run()

	// Initialize UDP manager
	udpManager := udp.NewUDPManager(udp.UDPConfig{
		ListenPort: ":8081",
		BufferSize: 1024,
	})

	if err := udpManager.Start(); err != nil {
		log.Fatalf("Failed to start UDP manager: %v", err)
	}
	defer udpManager.Stop()

	// Setup bridge antara UDP dan WebSocket
	go bridgeUDPToWebSocket(udpManager, wsManager)
	go bridgeWebSocketToUDP(wsManager, udpManager)

	// Setup router
	router := mux.NewRouter()

	// WebSocket route
	router.HandleFunc("/ws", wsManager.HandleWebSocket)

	// Health check
	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":      "ok",
			"udp_clients": udpManager.GetClientCount(),
			"timestamp":   time.Now(),
		})
	}).Methods("GET")

	// CORS configuration
	c := cors.New(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
	})

	handler := c.Handler(router)

	log.Println("REST API/WebSocket server starting on :8080")
	log.Println("UDP server starting on :8081")
	log.Fatal(http.ListenAndServe(":8080", handler))
}

// Bridge untuk meneruskan message dari UDP ke WebSocket
func bridgeUDPToWebSocket(udpManager *udp.UDPManager, wsManager *websocket.Manager) {
	for msg := range udpManager.GetReceiveChannel() {
		// Convert UDP message ke WebSocket message
		wsMessage := map[string]interface{}{
			"type":      "udp_message",
			"data":      msg,
			"from":      "udp_bridge",
			"timestamp": time.Now(),
		}

		messageBytes, err := json.Marshal(wsMessage)
		if err != nil {
			log.Printf("Error marshaling UDP to WS message: %v", err)
			continue
		}

		wsManager.BroadcastMessage(messageBytes)
		log.Printf("Bridged UDP message to WebSocket: %+v", msg)
	}
}

// Bridge untuk meneruskan message dari WebSocket ke UDP
func bridgeWebSocketToUDP(wsManager *websocket.Manager, udpManager *udp.UDPManager) {
	// Ini adalah simplified version, dalam real implementation
	// Anda perlu modify WebSocket manager untuk support receive channel
	log.Println("WebSocket to UDP bridge ready")
}
