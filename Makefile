
SRCS := $(shell find srcs -name '*.ml')
NAME = ft_turing

# EXERCISES := $(join $(addsuffix /,$(DIRS)),$(SRCS))

# RUN_TARGETS := $(addprefix run,$(shell seq 0 9))

all: $(NAME)

$(NAME):
	@echo "Compiling $@..."
	ocamlopt -o $@ $(SRCS)

clean:
	@echo "Cleaning up..."
	rm -f $(NAME)
	cd srcs; rm -f *.cmx *.o *.cmi;

.PHONY: all clean $(DIRS) $(RUN_TARGETS)