/**
 * AetherHound Native C++ DSP Matrix Core Implementation.
 */
#include "dsp_core.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <complex>

constexpr double PI = 3.14159265358979323846;

extern "C" {

void cpp_hanning_window(const double* input, double* output, int n) {
    if (n <= 1) {
        if (n == 1) output[0] = input[0];
        return;
    }
    double factor = 2.0 * PI / (n - 1);
    for (int i = 0; i < n; ++i) {
        double w = 0.5 * (1.0 - std::cos(i * factor));
        output[i] = input[i] * w;
    }
}

void cpp_welch_power_spectrum(
    const double* segs,
    int num_segs,
    int frame,
    double* out_psd_db,
    int out_bins
) {
    int rfft_bins = frame / 2 + 1;
    std::vector<double> psd_accum(rfft_bins, 0.0);

    for (int s = 0; s < num_segs; ++s) {
        const double* seg = segs + s * frame;
        // Compute Real-FFT Power Spectrum for this segment
        for (int k = 0; k < rfft_bins; ++k) {
            double real_part = 0.0;
            double imag_part = 0.0;
            double omega = 2.0 * PI * k / frame;
            for (int t = 0; t < frame; ++t) {
                double angle = omega * t;
                real_part += seg[t] * std::cos(angle);
                imag_part -= seg[t] * std::sin(angle);
            }
            psd_accum[k] += (real_part * real_part + imag_part * imag_part);
        }
    }

    double scale = 1.0 / (num_segs > 0 ? num_segs : 1);
    int limit = (out_bins < rfft_bins) ? out_bins : rfft_bins;
    for (int k = 0; k < limit; ++k) {
        double p = psd_accum[k] * scale;
        out_psd_db[k] = 10.0 * std::log10(p + 1e-12);
    }
}

void cpp_max_pool_reduce(
    const double* in_db,
    int in_len,
    const int* bin_indices,
    int nbins,
    double* out_pooled
) {
    for (int b = 0; b < nbins; ++b) {
        int start = bin_indices[b];
        int end = bin_indices[b + 1];
        if (start >= in_len) start = in_len - 1;
        if (end > in_len) end = in_len;
        if (end <= start) end = start + 1;

        double max_val = in_db[start];
        for (int i = start + 1; i < end; ++i) {
            if (in_db[i] > max_val) {
                max_val = in_db[i];
            }
        }
        out_pooled[b] = max_val;
    }
}

double cpp_topk_residual_score(
    const double* residuals,
    const double* mask,
    int nbins,
    int topk
) {
    std::vector<double> squared_res(nbins);
    for (int i = 0; i < nbins; ++i) {
        double r = residuals[i] * mask[i];
        squared_res[i] = r * r;
    }
    std::sort(squared_res.begin(), squared_res.end());

    int k = (topk > nbins) ? nbins : ((topk < 1) ? 1 : topk);
    double sum = 0.0;
    for (int i = nbins - k; i < nbins; ++i) {
        sum += squared_res[i];
    }
    return sum / k;
}

void cpp_adaptive_ema_update(
    double* mu,
    double* var,
    const double* feat,
    int nbins,
    double alpha
) {
    for (int i = 0; i < nbins; ++i) {
        double d = feat[i] - mu[i];
        mu[i] += alpha * d;
        double new_var = (1.0 - alpha) * var[i] + alpha * d * d;
        var[i] = (new_var > 0.25) ? new_var : 0.25;
    }
}

} // extern "C"
