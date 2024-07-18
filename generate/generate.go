package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"text/template"
)

type Build struct {
	Target string `json:"target"`
	CC     string `json:"cc"`
	GOOS   string `json:"goos"`
	GOARCH string `json:"goarch"`
}

type Matrix struct {
	Builds   []Build  `json:"build"`
	Services []string `json:"service"`
}

var (
	matrix  Matrix
	version string

	tpls = template.Must(template.ParseGlob("templates/*.tpl"))
)

func init() {
	json.Unmarshal([]byte(os.Getenv("MATRIX")), &matrix)
	version = os.Getenv("VERSION")
}

func genGoFile(build Build, service string) error {
	pkg := strings.ReplaceAll(service, "-", "_")
	pkgPath := fmt.Sprintf("../%s", pkg)

	_, err := os.Stat(pkgPath)
	if os.IsNotExist(err) {
		err := os.Mkdir(pkgPath, os.ModePerm)
		if err != nil {
			return err
		}
	}

	err = os.Rename(
		fmt.Sprintf("../libopendal_c_%s_%s_%s/libopendal_c.%s.so.zst", version, service, build.Target, build.Target),
		fmt.Sprintf("../%s/libopendal_c.%s.%s.so.zst", pkg, build.GOOS, build.GOARCH))
	if err != nil {
		return err
	}

	for _, t := range tpls.Templates() {
		fileTpl := template.Must(template.New("file").Parse(t.Name()))
		var buf bytes.Buffer
		err := fileTpl.Execute(&buf, map[string]string{
			"os":   build.GOOS,
			"arch": build.GOARCH,
		})
		if err != nil {
			return fmt.Errorf("parse filename: %s:%s", t.Name(), err)
		}
		targetFile := fmt.Sprintf("../%s/%s", pkg, strings.Trim(buf.String(), ".tpl"))
		os.Remove(targetFile)

		file, err := os.OpenFile(targetFile, os.O_CREATE|os.O_WRONLY, os.ModePerm)
		if err != nil {
			return fmt.Errorf("open file: %s: %s", t.Name(), err)
		}
		defer file.Close()

		if err := t.Execute(file, map[string]string{
			"pkg":  pkg,
			"os":   build.GOOS,
			"arch": build.GOARCH,
		}); err != nil {
			return fmt.Errorf("execute template: %s: %s", t.Name(), err)
		}
	}
	cmd := exec.Command("go", "mod", "tidy")
	cmd.Dir = pkgPath
	output, err := cmd.Output()
	if err != nil {
		return err
	}
	fmt.Printf("%s\n", output)
	return nil
}

func main() {
	for _, service := range matrix.Services {
		for _, build := range matrix.Builds {
			err := genGoFile(build, service)
			if err != nil {
				panic(fmt.Errorf("failed to generate go file: %s", err))
			}
		}
	}
}
