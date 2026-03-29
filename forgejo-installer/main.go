package main

import (
	"os"

	"github.com/dev-boffin-io/forgejo-installer/cmd"
)

func main() {
	cmd.Run(os.Args[1:])
}
