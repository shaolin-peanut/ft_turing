SRC_DIR = srcs
SRCS := $(SRC_DIR)/types.ml  $(SRC_DIR)/parser.ml $(SRC_DIR)/transition.ml $(SRC_DIR)/compute.ml $(SRC_DIR)/main.ml $(SRC_DIR)/encoder.ml
TEST_DIR = tests
TEST_SRCS := $(TEST_DIR)/test_utils.ml $(TEST_DIR)/parser_test.ml $(TEST_DIR)/test_machines.ml
BUILD_DIR = build
NAME = ft_turing
PKGS = yojson
PYTHON ?= python3

UTM_DECODER_DIR ?= machines/utm-samuel
UTM_OUT ?= utm_out.txt
UTM_LOG ?= utm_run.log
TM_MACHINE ?= machines/utm-marie/unary_add_forward.json
UTM_MACHINE ?= machines/utm-marie/utm_9_3_bootsrap.json
ENCODED_OUT ?= machines/input_encoded.txt
UTM_INPUT ?= 11+1=
UTM_SHOW ?= 400
UTM_CONTEXT ?= 80
UTM_TABLE ?= 8
UTM_VIZ_OUT ?= machines/utm-samuel/evidence6_report.html

ML_FILES := $(notdir $(SRCS))
OBJS := $(ML_FILES:.ml=.cmx)
OBJS := $(addprefix $(BUILD_DIR)/, $(OBJS))

TEST_FILES := $(notdir $(TEST_SRCS))
TEST_OBJS := $(TEST_FILES:.ml=.cmx)
TEST_OBJS := $(addprefix $(BUILD_DIR)/, $(TEST_OBJS))

all: $(BUILD_DIR) $(NAME)

test: $(BUILD_DIR) $(BUILD_DIR)/types.cmx $(BUILD_DIR)/parser.cmx $(BUILD_DIR)/transition.cmx $(BUILD_DIR)/compute.cmx $(TEST_OBJS) 
	@echo "Building and running tests..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -o $(BUILD_DIR)/test_runner $(BUILD_DIR)/types.cmx $(BUILD_DIR)/parser.cmx $(BUILD_DIR)/transition.cmx $(BUILD_DIR)/compute.cmx $(TEST_OBJS)
	./$(BUILD_DIR)/test_runner

# Règle pour compiler l'outil encoder
encoder: build/types.cmx build/parser.cmx srcs/encoder.ml
	ocamlfind ocamlopt -package yojson -linkpkg -I build -I srcs -o encoder build/types.cmx build/parser.cmx srcs/encoder.ml

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.cmx: srcs/%.ml
	@echo "Compiling $<..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -c $< -o $@

$(BUILD_DIR)/%.cmx: tests/%.ml
	@echo "Compiling test $<..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -c $< -o $@

$(NAME): $(OBJS)
	@echo "Linking $@..."
	ocamlfind ocamlopt -package $(PKGS) -linkpkg -I $(BUILD_DIR) -o $@ $(OBJS)

clean:
	@echo "Cleaning up..."
	rm -rf $(BUILD_DIR)

fclean: clean
	@echo "Removing executable..."
	rm -f $(NAME)
	rm -f encoder

re: fclean all

utm-decode:
	$(PYTHON) $(UTM_DECODER_DIR)/decode.py $(UTM_OUT)

utm-decode-evidence:
	$(PYTHON) $(UTM_DECODER_DIR)/decode_evidence.py $(UTM_OUT) $(TM_MACHINE) --input '$(UTM_INPUT)'

utm-decode2:
	$(PYTHON) $(UTM_DECODER_DIR)/decode_evidence2.py $(UTM_OUT) $(TM_MACHINE) --input '$(UTM_INPUT)' --show $(UTM_SHOW)

utm-encode: encoder
	./encoder $(TM_MACHINE) '$(UTM_INPUT)' > $(ENCODED_OUT)

utm-run: $(NAME) utm-encode
	./$(NAME) $(UTM_MACHINE) "$$(cat $(ENCODED_OUT))" > $(UTM_OUT)

utm-cycle: utm-run utm-decode2

utm-run-proof: $(NAME) utm-encode
	./$(NAME) $(UTM_MACHINE) "$$(cat $(ENCODED_OUT))" --quiet > $(UTM_OUT) 2> $(UTM_LOG)

utm-decode5:
	$(PYTHON) $(UTM_DECODER_DIR)/decode_evidence5.py $(UTM_OUT) $(TM_MACHINE) --input '$(UTM_INPUT)' --run-log $(UTM_LOG) --show $(UTM_SHOW)

utm-proof: utm-run-proof utm-decode5

utm-cycle5: utm-proof

utm-decode6:
	$(PYTHON) $(UTM_DECODER_DIR)/decode_evidence6.py $(UTM_OUT) $(TM_MACHINE) --input '$(UTM_INPUT)' --run-log $(UTM_LOG) --show $(UTM_SHOW) --context $(UTM_CONTEXT) --table $(UTM_TABLE)

utm-proof6: utm-run-proof utm-decode6

utm-cycle6: utm-proof6

utm-viz6:
	$(PYTHON) $(UTM_DECODER_DIR)/visualize_evidence6.py $(UTM_OUT) $(TM_MACHINE) --input '$(UTM_INPUT)' --run-log $(UTM_LOG) --out $(UTM_VIZ_OUT) --context $(UTM_CONTEXT)

utm-proof6-viz: utm-proof6 utm-viz6

utm-proof6-matrix:
	@set -e; \
	for I in "1+1=" "11+1=" "111+1=" "11+11="; do \
		echo ""; \
		echo "===================="; \
		echo "utm-proof6 input=$$I"; \
		echo "===================="; \
		$(MAKE) --no-print-directory utm-proof6 UTM_INPUT="$$I" UTM_SHOW=200 UTM_CONTEXT=60 UTM_TABLE=8; \
	done

utm-proof6-negatives:
	@set -e; \
	echo ""; \
	echo "===================="; \
	echo "negative: missing run log (expect FAIL)"; \
	echo "===================="; \
	if $(PYTHON) $(UTM_DECODER_DIR)/decode_evidence6.py $(UTM_OUT) $(TM_MACHINE) --input '$(UTM_INPUT)' --run-log /tmp/utm_run_missing.log > /tmp/sam_v6_neg1.txt 2>&1; then \
		echo "ERROR: expected failure, got success"; \
		cat /tmp/sam_v6_neg1.txt; \
		exit 1; \
	else \
		echo "OK: failed as expected"; \
	fi; \
	echo ""; \
	echo "===================="; \
	echo "negative: corrupted utm_out (expect FAIL)"; \
	echo "===================="; \
	$(PYTHON) -c "from pathlib import Path; p=Path(r'$(UTM_OUT)'); lines=[ln.strip() for ln in p.read_text().splitlines() if ln.strip()]; last=lines[-1].split() if lines else []; Path('/tmp/utm_out_corrupt_v6_eval.txt').write_text(' '.join(last[:200]) + '\\n')"; \
	if $(PYTHON) $(UTM_DECODER_DIR)/decode_evidence6.py /tmp/utm_out_corrupt_v6_eval.txt $(TM_MACHINE) --input '$(UTM_INPUT)' --run-log $(UTM_LOG) > /tmp/sam_v6_neg2.txt 2>&1; then \
		echo "ERROR: expected failure, got success"; \
		cat /tmp/sam_v6_neg2.txt; \
		exit 1; \
	else \
		echo "OK: failed as expected"; \
	fi

utm-proof6-eval: utm-proof6-matrix utm-proof6-negatives

utm-snippets:
	@echo "Copy/paste test snippets:"
	@echo ""
	@echo "  make utm-proof6 UTM_INPUT='11+1='"
	@echo "  make utm-proof6 UTM_INPUT='1+1='"
	@echo "  make utm-proof6 UTM_INPUT='11+11='"
	@echo ""
	@echo "  make utm-proof6-viz UTM_INPUT='11+1='"
	@echo "  make utm-viz6 UTM_INPUT='11+1=' UTM_CONTEXT=120 UTM_VIZ_OUT=machines/utm-samuel/evidence6_report.html"
	@echo ""
	@echo "  make utm-decode6 UTM_INPUT='11+1=' UTM_SHOW=700 UTM_CONTEXT=120 UTM_TABLE=20"
	@echo "  make utm-decode2 UTM_INPUT='11+1=' UTM_SHOW=600"
	@echo ""
	@echo "  make utm-proof6-matrix"
	@echo "  make utm-proof6-negatives UTM_INPUT='11+1='"
	@echo "  make utm-proof6-eval"
	@echo ""
	@echo "  make utm-run-proof UTM_INPUT='11+1='"
	@echo "  make utm-decode6 UTM_INPUT='11+1=' UTM_OUT=utm_out.txt UTM_LOG=utm_run.log"
	@echo ""
	@echo "Common overrides:"
	@echo "  TM_MACHINE=machines/utm-marie/unary_add_forward.json"
	@echo "  UTM_MACHINE=machines/utm-marie/utm_9_3_bootsrap.json"
	@echo "  UTM_OUT=utm_out.txt UTM_LOG=utm_run.log"
	@echo "  UTM_CONTEXT=80 UTM_TABLE=8 UTM_SHOW=400"

utm-help: utm-snippets

utm-new-files:
	git status --short

.PHONY: all clean fclean re test utm-decode utm-decode-evidence utm-decode2 utm-encode utm-run utm-cycle utm-run-proof utm-decode5 utm-proof utm-cycle5 utm-decode6 utm-proof6 utm-cycle6 utm-viz6 utm-proof6-viz utm-proof6-matrix utm-proof6-negatives utm-proof6-eval utm-snippets utm-help utm-new-files
