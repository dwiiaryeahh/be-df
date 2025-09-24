package udp

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"sync"
	"time"
)

type UDPMessage struct {
	Type      string      `json:"type"`
	Data      interface{} `json:"data"`
	From      string      `json:"from"`
	Timestamp time.Time   `json:"timestamp"`
}

type UDPConfig struct {
	ListenPort string
	RemoteAddr string // Optional: untuk mengirim ke remote address tertentu
	BufferSize int
}

type UDPManager struct {
	config      UDPConfig
	conn        *net.UDPConn
	sendChan    chan []byte
	receiveChan chan UDPMessage
	clients     map[string]net.Addr
	mutex       sync.RWMutex
	running     bool
}

func NewUDPManager(config UDPConfig) *UDPManager {
	if config.BufferSize == 0 {
		config.BufferSize = 1024
	}

	return &UDPManager{
		config:      config,
		sendChan:    make(chan []byte, 100),
		receiveChan: make(chan UDPMessage, 100),
		clients:     make(map[string]net.Addr),
		running:     false,
	}
}

func (m *UDPManager) Start() error {
	udpAddr, err := net.ResolveUDPAddr("udp", m.config.ListenPort)
	if err != nil {
		return fmt.Errorf("error resolving UDP address: %v", err)
	}

	conn, err := net.ListenUDP("udp", udpAddr)
	if err != nil {
		return fmt.Errorf("error listening on UDP: %v", err)
	}

	m.conn = conn
	m.running = true

	log.Printf("UDP Server started on %s", m.config.ListenPort)

	// Start goroutines untuk handling
	go m.receiveLoop()
	go m.sendLoop()
	go m.broadcastLoop()

	return nil
}

func (m *UDPManager) Stop() {
	m.running = false
	if m.conn != nil {
		m.conn.Close()
	}
	close(m.sendChan)
	close(m.receiveChan)
}

func (m *UDPManager) receiveLoop() {
	buffer := make([]byte, m.config.BufferSize)

	for m.running {
		n, addr, err := m.conn.ReadFromUDP(buffer)
		if err != nil {
			if m.running {
				log.Printf("Error reading from UDP: %v", err)
			}
			continue
		}

		// Simpan client address
		m.mutex.Lock()
		m.clients[addr.String()] = addr
		m.mutex.Unlock()

		// Process received data
		if n > 0 {
			var msg UDPMessage
			if err := json.Unmarshal(buffer[:n], &msg); err != nil {
				// Jika bukan JSON, treat as plain text
				msg = UDPMessage{
					Type:      "text",
					Data:      string(buffer[:n]),
					From:      addr.String(),
					Timestamp: time.Now(),
				}
			} else {
				msg.From = addr.String()
				msg.Timestamp = time.Now()
			}

			// Kirim ke receive channel
			select {
			case m.receiveChan <- msg:
			default:
				log.Println("Receive channel full, dropping message")
			}

			log.Printf("Received UDP message from %s: %s", addr.String(), string(buffer[:n]))
		}
	}
}

func (m *UDPManager) sendLoop() {
	for m.running {
		select {
		case data, ok := <-m.sendChan:
			if !ok {
				return
			}
			m.broadcastToClients(data)
		}
	}
}

func (m *UDPManager) broadcastLoop() {
	// Broadcast heartbeat setiap 30 detik
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for m.running {
		select {
		case <-ticker.C:
			heartbeat := UDPMessage{
				Type:      "heartbeat",
				Data:      "UDP Server Alive",
				From:      "server",
				Timestamp: time.Now(),
			}
			m.BroadcastMessage(heartbeat)
		}
	}
}

func (m *UDPManager) broadcastToClients(data []byte) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	for _, addr := range m.clients {
		if _, err := m.conn.WriteToUDP(data, addr.(*net.UDPAddr)); err != nil {
			log.Printf("Error sending to %s: %v", addr.String(), err)
		}
	}
}

func (m *UDPManager) SendTo(address string, data []byte) error {
	udpAddr, err := net.ResolveUDPAddr("udp", address)
	if err != nil {
		return err
	}

	_, err = m.conn.WriteToUDP(data, udpAddr)
	return err
}

func (m *UDPManager) BroadcastMessage(message UDPMessage) error {
	data, err := json.Marshal(message)
	if err != nil {
		return err
	}

	select {
	case m.sendChan <- data:
	default:
		return fmt.Errorf("send channel full")
	}
	return nil
}

func (m *UDPManager) GetReceiveChannel() <-chan UDPMessage {
	return m.receiveChan
}

func (m *UDPManager) GetClientCount() int {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return len(m.clients)
}
