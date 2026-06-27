package joiner

func JoinRows(rows [][]string) string {
	out := ""
	for _, row := range rows {
		line := ""
		for i, field := range row {
			if i > 0 {
				line = line + ","
			}
			line = line + field
		}
		out = out + line + "\n"
	}
	return out
}
