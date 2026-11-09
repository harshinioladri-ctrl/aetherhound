"""Python ctypes bridge to native C++ DSP acceleration core (Week 4 Deliverable).
Dynamically checks for libaetherhound_dsp.so / aetherhound_dsp.dll.
Falls back transparently to optimized NumPy if the C++ library is not compiled.
"""
import ctypes, os, sys
import numpy as np

_cpp_lib = None
_lib_paths = [
    os.path.join(os.path.dirname(__file__), "..", "src_cpp", "aetherhound_dsp.dll"),
    os.path.join(os.path.dirname(__file__), "..", "src_cpp", "libaetherhound_dsp.so"),
    os.path.join(os.path.dirname(__file__), "..", "src_cpp", "libaetherhound_dsp.dylib"),
    os.path.join(os.path.dirname(__file__), "aetherhound_dsp.dll"),
    os.path.join(os.path.dirname(__file__), "libaetherhound_dsp.so"),
]

for p in _lib_paths:
    if os.path.exists(p):
        try:
            _cpp_lib = ctypes.CDLL(os.path.abspath(p))
            # Define signatures
            _cpp_lib.cpp_hanning_window.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_int
            ]
            _cpp_lib.cpp_max_pool_reduce.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_int),
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_double)
            ]
            _cpp_lib.cpp_topk_residual_score.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_int,
                ctypes.c_int
            ]
            _cpp_lib.cpp_topk_residual_score.restype = ctypes.c_double
            break
        except Exception:
            _cpp_lib = None

def has_cpp_acceleration():
    return _cpp_lib is not None

def hanning_window(x):
    """Applies Hanning window with C++ acceleration if available."""
    n = len(x)
    if _cpp_lib is not None:
        out = np.empty(n, dtype=np.float64)
        in_ptr = x.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        out_ptr = out.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        _cpp_lib.cpp_hanning_window(in_ptr, out_ptr, n)
        return out
    return x * np.hanning(n)

def max_pool_reduce(db_vector, bin_indices, nbins):
    """Max-pooling reduction with C++ acceleration if available."""
    if _cpp_lib is not None:
        db_vec = np.ascontiguousarray(db_vector, dtype=np.float64)
        indices = np.ascontiguousarray(bin_indices, dtype=np.int32)
        out = np.empty(nbins, dtype=np.float64)
        _cpp_lib.cpp_max_pool_reduce(
            db_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            len(db_vec),
            indices.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            nbins,
            out.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        )
        return out
    return np.maximum.reduceat(db_vector, bin_indices[:-1])

def topk_residual_score(residuals, mask, topk):
    """Computes Top-K anomaly score with C++ acceleration if available."""
    nbins = len(residuals)
    if _cpp_lib is not None:
        res = np.ascontiguousarray(residuals, dtype=np.float64)
        m = np.ascontiguousarray(mask, dtype=np.float64)
        return float(_cpp_lib.cpp_topk_residual_score(
            res.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            m.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            nbins,
            topk
        ))
    return float(np.sort((residuals * mask) ** 2)[-topk:].mean())
