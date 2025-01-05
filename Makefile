SRC_DIR = srcs
SRCS := $(SRC_DIR)/types.ml $(SRC_DIR)/parser.ml $(SRC_DIR)/main.ml
TEST_DIR = tests
TEST_SRCS := $(TEST_DIR)/test_utils.ml $(TEST_DIR)/parser_test.ml
BUILD_DIR = build
NAME = ft_turing
PKGS = yojson

ML_FILES := $(notdir $(SRCS))
OBJS := $(ML_FILES:.ml=.cmx)
OBJS := $(addprefix $(BUILD_DIR)/, $(OBJS))

TEST_FILES := $(notdir $(TEST_SRCS))
TEST_OBJS := $(TEST_FILES:.ml=.cmx)
TEST_OBJS := $(addprefix $(BUILD_DIR)/, $(TEST_OBJS))

all: $(BUILD_DIR) $(BUILD_DIR)/$(NAME)

test: $(BUILD_DIR) $(BUILD_DIR)/types.cmx $(BUILD_DIR)/parser.cmx $(TEST_OBJS)
	@echo "Building and running tests..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -o $(BUILD_DIR)/test_runner $(BUILD_DIR)/types.cmx $(BUILD_DIR)/parser.cmx $(TEST_OBJS)
	./$(BUILD_DIR)/test_runner

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.cmx: srcs/%.ml
	@echo "Compiling $<..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -c $< -o $@

$(BUILD_DIR)/%.cmx: tests/%.ml
	@echo "Compiling test $<..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -c $< -o $@

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

.PHONY: all clean fclean re test