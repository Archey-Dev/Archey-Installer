# ── Archey C++ Installer — Makefile ──────────────────────────────────────────
# Requires: qt6-base gcc
# On Arch:  sudo pacman -S qt6-base gcc

CXX    := g++
TARGET := archey
SRCDIR := src
BDIR   := build

# ── Qt6: use qmake6 to find headers/libs ─────────────────────────────────────
QMAKE6 := $(shell which qmake6 2>/dev/null || which qmake 2>/dev/null)
ifeq ($(QMAKE6),)
  $(error qmake6 not found. Install with: sudo pacman -S qt6-base)
endif

QT_HEADERS  := $(shell $(QMAKE6) -query QT_INSTALL_HEADERS)
QT_LIBS_DIR := $(shell $(QMAKE6) -query QT_INSTALL_LIBS)
QT_BINS     := $(shell $(QMAKE6) -query QT_INSTALL_BINS)

# ── Find moc: QT_INSTALL_BINS/moc first, then search the system ──────────────
# On Arch with both Qt5+Qt6, /usr/bin/moc may be Qt5. We need Qt6's moc.
# Qt6 moc on Arch is typically at /usr/lib/qt6/bin/moc or in QT_INSTALL_BINS.
MOC := $(shell \
  for candidate in \
    "$(QT_BINS)/moc" \
    "/usr/lib/qt6/bin/moc" \
    "$(shell find /usr -name moc -executable -path '*/qt6/*' 2>/dev/null | head -1)" \
  ; do \
    if [ -x "$$candidate" ]; then echo "$$candidate"; break; fi; \
  done)

QT_CFLAGS := -I$(QT_HEADERS) \
             -I$(QT_HEADERS)/QtWidgets \
             -I$(QT_HEADERS)/QtCore \
             -I$(QT_HEADERS)/QtGui \
             -DQT_WIDGETS_LIB -DQT_GUI_LIB -DQT_CORE_LIB

QT_LIBS := -L$(QT_LIBS_DIR) -lQt6Widgets -lQt6Core -lQt6Gui

# ── Compiler flags ─────────────────────────────────────────────────────────────
CXXFLAGS := -std=c++20 -O2 -Wall -Wextra -Wno-unused-parameter \
            -I$(SRCDIR) $(QT_CFLAGS) -fPIC
LDFLAGS  := $(QT_LIBS) -lpthread

# ── Targets ───────────────────────────────────────────────────────────────────
.PHONY: all clean install info

all: info $(TARGET)

info:
	@echo "  qmake : $(QMAKE6)"
	@echo "  moc   : $(MOC)"
	@echo "  Qt    : $(QT_HEADERS)"
	@test -n "$(MOC)" || (echo "" && \
	  echo "ERROR: Could not find Qt6 moc binary." && \
	  echo "       Run: find /usr -name moc -executable 2>/dev/null" && \
	  echo "       Then set: make MOC=/path/to/qt6/moc" && exit 1)

$(BDIR):
	mkdir -p $(BDIR)

$(BDIR)/moc_all.cpp: $(wildcard $(SRCDIR)/*.h) | $(BDIR)
	@echo "[moc] processing Q_OBJECT headers..."
	@printf '' > $@
	@cd $(SRCDIR) && for h in *.h; do \
	    if grep -q "Q_OBJECT" "$$h"; then \
	        printf "  moc  $$h\n"; \
	        "$(MOC)" $(QT_CFLAGS) "$$h" >> ../$@ \
	            || (echo "FATAL: moc failed on $$h" && exit 1); \
	    fi; \
	done
	@test -s $@ || (echo "FATAL: moc_all.cpp is empty" && exit 1)

$(BDIR)/moc_all.o: $(BDIR)/moc_all.cpp | $(BDIR)
	@echo "[c++] moc_all"
	@$(CXX) $(CXXFLAGS) -c $< -o $@

$(BDIR)/main.o: $(SRCDIR)/main.cpp $(wildcard $(SRCDIR)/*.h) | $(BDIR)
	@echo "[c++] main.cpp"
	@$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(BDIR)/main.o $(BDIR)/moc_all.o
	@echo "[ld]  $(TARGET)"
	@$(CXX) $^ $(LDFLAGS) -o $@
	@echo ""
	@echo "  ✓  ./$(TARGET)   ($$(du -sh $(TARGET) | cut -f1))"

install: $(TARGET)
	install -Dm755 $(TARGET) /usr/local/bin/$(TARGET)

clean:
	rm -rf $(BDIR) $(TARGET)
