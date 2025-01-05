SRC_DIR = srcs
SRCS := $(SRC_DIR)/types.ml $(SRC_DIR)/parser.ml $(SRC_DIR)/main.ml
BUILD_DIR = build
NAME = ft_turing
PKGS = yojson

ML_FILES := $(notdir $(SRCS)) # Extract file names from srcs
OBJS := $(ML_FILES:.ml=.cmx) # Replace .ml with .cmx for object files
OBJS := $(addprefix $(BUILD_DIR)/, $(OBJS)) # Add build dir prefix

all: $(BUILD_DIR) $(BUILD_DIR)/$(NAME)

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

# Compile source files into the build directory
$(BUILD_DIR)/%.cmx: srcs/%.ml
	@echo "Compiling $<..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -c $< -o $@

# Link the final executable
$(BUILD_DIR)/$(NAME): $(OBJS)
	@echo "Linking $@..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -o $@ $(OBJS)

clean:
	@echo "Cleaning up..."
	rm -rf $(BUILD_DIR)

fclean: clean
	@echo "Removing executable..."
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
