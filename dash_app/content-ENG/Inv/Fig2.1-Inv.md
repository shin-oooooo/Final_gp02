## 1. Holdout

“Holdout” is a classic A/B mechanism in internet products and ML: hold out a small fraction of users (often 1%–10%) who never see new policies or models and stay on the legacy experience.

## 2. Shadow model selection & scoring dimensions

“Shadow model selection” uses “Holdout” as the primary holdout mechanism to choose the best model per symbol. The main dimensions are: **point prediction**—predicted vs. realized return levels, scored with variance; **probabilistic prediction**—overlap between predicted and realized return densities, scored with JSD. Model composite scores linearly combine the two (α is MSE weight, 1−α is JSD weight). α closer to 1 stresses point accuracy; closer to 0 stresses density overlap. A tail slice of the training sample of configurable length acts as pseudo out-of-sample to compute MSE and JSD; shorter slices run faster but are less precise.

## 3. Tunable parameters

α and “shadow model selection” window length are adjusted in the “custom parameter panel.”

## 4. Reading the pixel matrix

Each lit cell means that symbol’s best model under the shadow composite score (Naive / ARIMA / LightGBM / Kronos).
