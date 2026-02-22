---
title: 'Building a prediction model to detect spam email'
date: 2023-08-19
description: "Using the spam email dataset from Tidy Tuesday Week 33, I walk through the process of building and evaluating a prediction model using decision tree and random forest machine learning algorithms."
image: social-image.png
options:
  categories:
    - machine-learning
    - R
---

Getting back into the swing of things. This is my first blog post in more than 3 years!

For this post, I'll be using the Week 33 [Tidy Tuesday](https://github.com/rfordatascience/tidytuesday) dataset. This one is all about spam email.

From the <a href="https://vincentarelbundock.github.io/Rdatasets/doc/DAAG/spam7.html">dataset description</a>:

> The data consist of 4601 email items, of which 1813 items were identified as spam. This is a subset of the full dataset, with six only of the 57 explanatory variables in the complete dataset.


```r
library(tidyverse)
library(caret)
library(corrplot)
library(tidymodels)
library(usemodels)
library(future)
library(rpart)
library(rpart.plot)
knitr::opts_chunk$set(echo = TRUE, fig.width = 4.5, fig.height = 2.5)
```

# Load data

```r
df <- readr::read_csv('https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2023/2023-08-15/spam.csv') %>%
  mutate(yesno = factor(yesno == 'y', levels=c(TRUE, FALSE)))
```

# Data dictionary

```
variable    class         description
crl.tot     double        Total length of uninterrupted sequences of capitals
dollar      double        Occurrences of the dollar sign, as percent of total number of characters
bang        double        Occurrences of '!', as percent of total number of characters
money       double        Occurrences of 'money', as percent of total number of characters
n000        double        Occurrences of the string '000', as percent of total number of words
make        double        Occurrences of 'make', as a percent of total number of words
yesno       character     Outcome variable, a factor with levels 'n' not spam, 'y' spam
```

The outcome variable is `yesno`, a character type, and all of the other variables are of a numeric type.

We can see that a lot of the feature engineering has already been done. It seems that whoever prepared this dataset has determined that spam emails can be meaningfully identified by:

- SHOUTING! (`crl.tot`, `bang`)
- and talk of making money (`make`, `money`, `dollar`) at values of 1,000 or greater (`n000`)

That definitely matches my experience reading spam!


# What can we do with this data?

What can we do with this data? Because this data has "ground truth" labels that tell us which emails were spam or not (`yesno`), and a list of features associated with each email, we can approach this as a supervised ML problem. We can use supervised ML to predict spam, to create a spam filter, for example.

# Supervised ML: Predicting spam / spam filter

## Average values, by spam

Let's start by looking at some averages (mean and median), split by the outcome variable.

```r
df %>%
  group_by(yesno) %>%
  summarise_all(mean)
```

We can see that on average, spam emails have higher mean values for each of the predictors. No surprise there.

However, the medians of some variables are zero, which suggests those variables have heavily positively skewed distributions with many zero values (sometimes called "zero-inflation").

```r
df %>%
  group_by(yesno) %>%
  summarise_all(median)
```

We can confirm this by looking at the counts of zero values, in relation to the total counts.

As we see, the vast majority of the spam emails had non-zero values on these variables, and non-spam emails had significantly fewer non-zero values, with the exception of `crl.tot`. In particular, spam emails were MUCH more likely to contain "!", "$", "000", and "money".

```r
no = df %>% filter(yesno == FALSE) %>% select(-yesno)
yes = df %>% filter(yesno == TRUE) %>% select(-yesno)

round(colSums(no>0)/nrow(no)*100)
round(colSums(yes>0)/nrow(yes)*100)
```

## Distributions, by spam

Next, let's look at the distributions.

For these plots, since they all have extreme skew, I'm going to truncate them at the 90th percentile and look at the left side where most of the mass is.

```r
for (c in c('crl.tot', 'dollar', 'bang', 'money', 'n000', 'make')){

  qtile_90 <- quantile(df[[c]], .90)

  df %>%
    filter(!!sym(c) < qtile_90) %>%
    ggplot(aes(x = !!sym(c), fill=yesno)) +
      geom_density(alpha=.7) +
      ggtitle(c) -> plot
  print(plot)

}
```

## Feature correlations

It doesn't look like the features are very strongly correlated. The strongest correlation is between `n000` and `dollar`, which is not particularly surprising since I would expect that "000" would tend to appear in the context of a dollar value like "$1000".

```r
df %>%
  select(-yesno) %>%
  cor(use = "complete.obs")
```
If we convert the features to boolean, we can see that the presence of features have stronger correlations. The strongest correlation is again between `dollar` and `n000`, but `money` and `dollar` also occur together more often than not.

```r
df %>%
  select(-yesno, -crl.tot) %>%
  mutate(dollar = dollar > 0,
         bang = bang > 0,
         money = money > 0,
         n000 = n000 > 0,
         make = make > 0
  ) %>%
  cor(use = "complete.obs")
```

## Simple classification algorithm

Just for fun, let's see how well we can distinguish spam vs. not spam using a simple heuristic.

I'll label anything as spam if it contained at least 1 "money", "$", "000", and "!" OR if it contained more than 100 uninterrupted sequences of capital letters and at least 1 "!". This is just what comes to mind after looking at the frequency plots above.

```r
df %>%
  mutate(simple_spam_flag = factor((money > 0 & dollar > 0 & bang > 0 & n000 > 0) |
                                     (crl.tot > 100 & bang > 0),
                                   levels=c(TRUE, FALSE))
         ) -> df_flag
```

This simple classification algorithm achieved an accuracy of 79%, with 64% sensitivity and 89% specificity. This doesn't seem too bad. But what is a good baseline of performance?

```r
confusionMatrix(df_flag$simple_spam_flag, df_flag$yesno, mode='everything')
```
We can see that the base rate of spam is 39%.

```r
mean(df$yesno == TRUE)
```

A good baseline model might be to predict the majority class, which in this case is not-spam.

This "always predict FALSE" baseline model can be expected to achieve 1 minus the base rate of spam (i.e., 61%), and we can see that this is the case if we construct just such a model. This tells us that the heuristic model above is quite a bit better than a completely naive model.

```r
confusionMatrix(factor(rep('FALSE',nrow(df_flag))), df_flag$yesno, mode='everything')
```



## Decision Tree

Proceeding from simpler to more complex, we can go a step further and try fitting a decision tree model. The decision tree will help us to identify a more sophisticated rule set for classifying spam mail. Decision trees also have the advantage of being highly interpretable.

We'll start by splitting our data into training and test -- that way, we won't be testing performance on the same data that our model was trained on, and we can minimize the risk of overfitting.

```r
set.seed(200)
split <- initial_split(df)
train <- training(split)
test <- testing(split)
```

Next, we'll fit the model and then visualize its logic.

We can read this chart by starting at the root node and following the branches until we reach a terminal node. The predicted value at this terminal node will give us the prediction that the model has made, and the path that we followed to get there provides its reasoning for the prediction.

So for example, if we follow the tree to the left-most terminal node, we can see that it would predict that an email was spam if it contained `dollar >= 0.056`. If we follow the tree to the right-most terminal, we can see that it would predict that an email was not spam if it contained `dollar < 0.056` and `bang >= 0.12`. The percentage value in the node tells us what percentage of emails met these criteria. So 24% of emails met the former criteria, and 54% the latter.

```r
decision_tree <- rpart(yesno ~ ., data=train, method='class')
decision_tree
rpart.plot(decision_tree)
```

Finally, we can test the model on the out-of-sample test dataset and see how it performs.

Overall it achieved an accuracy of 85%, with 78% sensitivity and 89% specificity. This model has similar specificity as the heuristic model, but better sensitivity, and therefore better overall accuracy.

```r
test_pred <- predict(decision_tree, test, type='class')
confusionMatrix(test_pred, test$yesno, mode='everything')
```

## Random forest

Next, we'll try a random forest model. Random forest models tend to perform better than decision trees, due to the fact that they are ensemble decision trees, meaning they group together the decisions of lots of decision trees. But as a result, they tend to be less interpretable. So if our goal was only to create the most accurate prediction model possible, then a random forest would be better suited to the task.

```r
cv <- vfold_cv(train)
```

I'll use `usemodels::use_ranger` to give me a starting template.

```r
use_ranger(yesno ~ ., train)
```

I'll remove the parameter tuning to keep things simple.

```r
ranger_recipe <-
  recipe(formula = yesno ~ ., data = df)

ranger_spec <-
  rand_forest(trees = 1000) %>%
  set_mode("classification") %>%
  set_engine("ranger")

ranger_workflow <-
  workflow() %>%
  add_recipe(ranger_recipe) %>%
  add_model(ranger_spec)
```

Next, I'll fit the model using a resampling approach.

```r
set.seed(100)
plan(multisession)

fit_rf <- fit_resamples(
  ranger_workflow,
  cv,
  metrics = metric_set(accuracy, sens, spec),
  control = control_resamples(verbose = TRUE,
                              save_pred = TRUE,
                              extract = function(x) x)
)
```

Overall, accuracy is pretty good: 89% accuracy, 79% sensitivity, and 95% specificity.

```r
fit_rf %>%
  collect_metrics()
```
Next, we can check the performance on the test set.

We can use `collect_metrics()` function on the last fit.

```r
ranger_workflow %>%
  last_fit(split) %>%
  collect_metrics()
```

Or we can use `confusionMatrix()` to get a bit more information.

Performance on the test set is similar to the training performance. Overall, accuracy is pretty good -- and better than the decision tree. For a spam detection filter, we'd want to bias towards minimizing false positives (it would arguably be worse for people to lose legitimate mail to the filter, than to have spam mail slip through), and here we see that the specificity was quite good at ~95%.

```r
ranger_workflow %>%
  last_fit(split) %>%
  extract_workflow() -> final_model

confusionMatrix(predict(final_model, test)$.pred_class, test$yesno, mode='everything', positive='TRUE')
```