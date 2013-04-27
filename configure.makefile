build:
	true

install:
	install -d "%(bin)s"
	install -d "%(lib)s"
	install ajaxterm.bin "%(bin)s/ajaxterm"
	install -m 644 ajaxterm.css ajaxterm.html ajaxterm.js qweb.py sarissa.js sarissa_dhtml.js utf8-escape.js "%(lib)s"
	install -m 755 ajaxterm.py "%(lib)s"
	gzip --best -c ajaxterm.1 > ajaxterm.1.gz
	install -d "%(man)s"
	install ajaxterm.1.gz "%(man)s"

clean:
	rm ajaxterm.bin
	rm ajaxterm.1.gz
	rm Makefile

