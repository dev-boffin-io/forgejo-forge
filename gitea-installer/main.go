package main

import (
	"os"

	"github.com/dev-boffin-io/gitea-installer/cmd"
)

func main() {
	cmd.Run(os.Args[1:])
}
