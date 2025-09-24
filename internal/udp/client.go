package udp

import (
	"encoding/json"
	"log"
	"net"
	"time"
)

type UDPClient struct {
	serverAddr string
	conn       *net.UDPConn
	localPort  string
	running    bool
}

func NewUDPClient(serverAddr, localPort string) *UDPClient {
	return &UDPClient{
		serverAddr: serverAddr,
		localPort:  localPort,
		running:    false,
	}
}

func (c *UDPClient) Connect() error {
	localAddr, err := net.ResolveUDPAddr("udp", c.localPort)
	if err != nil {
		return err
	}

	conn, err := net.ListenUDP("udp", localAddr)
	if err != nil {
		return err
	}

	c.conn = conn
	c.running = true

	log.Printf("UDP Client started on %s", c.localPort)

	go c.receiveLoop()

	// Send registration message
	return c.SendMessage(UDPMessage{
		Type: "register",
		Data: "Client connected",
		From: c.localPort,
	})
}

func (c *UDPClient) Disconnect() {
	c.running = false
	if c.conn != nil {
		c.conn.Close()
	}
}

func (c *UDPClient) SendMessage(message UDPMessage) error {
	message.Timestamp = time.Now()
	data, err := json.Marshal(message)
	if err != nil {
		return err
	}

	serverUDPAddr, err := net.ResolveUDPAddr("udp", c.serverAddr)
	if err != nil {
		return err
	}

	_, err = c.conn.WriteToUDP(data, serverUDPAddr)
	if err != nil {
		return err
	}

	log.Printf("Sent message to %s: %s", c.serverAddr, string(data))
	return nil
}

func (c *UDPClient) receiveLoop() {
	buffer := make([]byte, 1024)

	for c.running {
		n, addr, err := c.conn.ReadFromUDP(buffer)
		if err != nil {
			if c.running {
				log.Printf("Error reading from UDP: %v", err)
			}
			continue
		}

		if n > 0 {
			var msg UDPMessage
			if err := json.Unmarshal(buffer[:n], &msg); err != nil {
				log.Printf("Received raw message from %s: %s", addr.String(), string(buffer[:n]))
			} else {
				log.Printf("Received message from %s: %+v", addr.String(), msg)
			}
		}
	}
}

func (c *UDPClient) SendTextMessage(text string) error {
	return c.SendMessage(UDPMessage{
		Type: "text",
		Data: text,
		From: c.localPort,
	})
}
