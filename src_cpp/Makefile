CXX ?= g++
CXXFLAGS ?= -O3 -Wall -fPIC -std=c++17 -fopenmp
TARGET = libaetherhound_dsp.so

ifeq ($(OS),Windows_NT)
    TARGET = aetherhound_dsp.dll
    LDFLAGS += -shared
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        TARGET = libaetherhound_dsp.dylib
        LDFLAGS += -dynamiclib
    else
        LDFLAGS += -shared
    endif
endif

all: $(TARGET)

$(TARGET): dsp_core.cpp dsp_core.h
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ dsp_core.cpp

clean:
	rm -f $(TARGET) *.o
