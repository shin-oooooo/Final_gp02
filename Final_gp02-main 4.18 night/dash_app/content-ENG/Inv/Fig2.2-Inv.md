## How to read the chart

Pick a symbol in the search box to see how each model’s predicted return density evolves over time on Fig2.2. The axis is the mean of the density; darker color means higher density at that return.

## Why it looks “stepwise”

At time t the model uses all history up to t, so each timestamp can involve refitting. To balance accuracy and speed, on the official test set we only refit parameters every few steps using information strictly before the current time—hence the staircase pattern. Fewer refits mean faster runs but lower accuracy.
