TARGETS = release/white-bunnybat.ttf release/white-bunnybat.woff release/white-bunnybat.woff2

all: $(TARGETS)

release/white-bunnybat.%: white-bunnybat.sfd
	./build.sh

clean:
	rm -f $(TARGETS)
.PHONY: all clean
