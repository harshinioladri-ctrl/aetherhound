/**
 * AetherHound Week 4 Performance Optimization: Native C++ DSP Matrix Core.
 * Accelerates windowed FFT, Welch PSD averaging, max-pooling reduction,
 * and top-k anomaly residual scoring.
 */
#ifndef AETHERHOUND_DSP_CORE_H
#define AETHERHOUND_DSP_CORE_H

#ifdef _WIN32
  #define DSP_EXPORT __declspec(dllexport)
#else
  #define DSP_EXPORT __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Applies Hanning window in-place: out[i] = in[i] * 0.5 * (1 - cos(2*pi*i/(n-1)))
 */
DSP_EXPORT void cpp_hanning_window(const double* input, double* output, int n);

/**
 * Fast Discrete Fourier Transform Power Spectrum (Welch PSD accumulator).
 */
DSP_EXPORT void cpp_welch_power_spectrum(
    const double* segs,
    int num_segs,
    int frame,
    double* out_psd_db,
    int out_bins
);

/**
 * Fast max-pooling reduction from full spectrum bins into nbins.
 */
DSP_EXPORT void cpp_max_pool_reduce(
    const double* in_db,
    int in_len,
    const int* bin_indices,
    int nbins,
    double* out_pooled
);

/**
 * Top-K Anomaly Residual Score calculation with frequency mask.
 */
DSP_EXPORT double cpp_topk_residual_score(
    const double* residuals,
    const double* mask,
    int nbins,
    int topk
);

/**
 * Exponential Moving Average (EMA) baseline update:
 * mu = mu + alpha * (feat - mu)
 * var = (1 - alpha) * var + alpha * (feat - mu)^2
 */
DSP_EXPORT void cpp_adaptive_ema_update(
    double* mu,
    double* var,
    const double* feat,
    int nbins,
    double alpha
);

#ifdef __cplusplus
}
#endif

#endif // AETHERHOUND_DSP_CORE_H
