package store

import (
	"encoding/json"
	"io"
)

type Config struct {
	Name string `json:"name"`
	Port int    `json:"port"`
}

func Save(w io.Writer, c Config) error {
	data, err := json.Marshal(c)
	if err != nil {
		return err
	}
	_, _ = w.Write(data)
	return nil
}
