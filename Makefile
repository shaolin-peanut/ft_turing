SRCS := $(shell find srcs -name '*.ml')
NAME = ft_turing
PKGS = yojson

all: $(NAME)

$(NAME):
	@echo "Compiling $@..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -o $@ $(SRCS)

clean:
	@echo "Cleaning up..."
	rm -f $(NAME)
	cd srcs; rm -f *.cmx *.o *.cmi;

.PHONY: all clean $(NAME)
