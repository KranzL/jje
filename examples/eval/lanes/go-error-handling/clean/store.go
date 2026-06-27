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
	if _, err := w.Write(data); err != nil {
		return err
	}
	return nil
}
