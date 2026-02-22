---
title: 'Using data normalization to better compare change over time in regions with different population sizes'
date: 2023-08-25
description: "I use data normalization to better compare the changes in refugee outflows in different regions from 2010 to 2022. Four regions are identified with large increases over their 2010 baseline."
image: social-image.png
options:
  categories:
    - R
---

For this post, I'll be using the Week 34 [Tidy Tuesday](https://github.com/rfordatascience/tidytuesday) dataset, which contains data on refugee movement around the world. I want to look at the change in refugee outflows over time in different nations, and see if I can identify countries with meaningfully large increases in refugee outflows.

```r
library(tidyverse)
library(wbstats)
library(gghighlight)
df <- readr::read_csv('https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2023/2023-08-22/population.csv')
```

# Data cleaning

First, some data cleaning.

To keep things simple, I'm only going to keep nations that had refugee data for all of the 13 years spanning 2010-2022.

```r
(df %>%
  group_by(coo_name) %>%
  summarize(n_years = n_distinct(year)) %>%
  filter(n_years == 13))$coo_name -> coo_to_keep

df %>%
  filter(coo_name %in% coo_to_keep) %>%
  select(coo_name,
         coo_iso,
         year,
         refugees) -> df_clean
```

# Normalization

Next, to make comparisons between nations more apples-apples, I'm going to do some normalization.

I want to normalize in terms of population size and change over baseline.

First, I'll fetch population data from World Bank using `wbstats`.

```r
wb_search("SP.POP.TOTL", fields='indicator_id') %>%
  head(1)
```

```r
pops <- wb_data("SP.POP.TOTL", start_date = 2010, end_date = 2022) %>%
  select(iso3c, date, "SP.POP.TOTL") %>%
  rename(pop = "SP.POP.TOTL",
         iso = iso3c)

df_clean %>%
  left_join(pops, by=c('coo_iso'='iso', 'year'='date')) -> df_enriched

df_enriched %>%
  head()
```

Next, I'll compute a new variable: `refugees_per_1k_pop` that represents refugees leaving per 1000 persons in the original population. This is a good way to normalize, because we'd expect a larger count of refugees leaving from countries that had more people to begin with.

```r
df_enriched %>%
  group_by(year, coo_name, coo_iso) %>%
  summarize(refugees = sum(refugees),
            pop = first(pop)) %>%
  mutate(refugees_per_1k_pop = refugees/(pop/1000)) -> df_enriched

df_enriched %>%
  head()
```

I'll do a bit of cleaning again, to remove those nations for whom I didn't have a complete record of population data, and so couldn't calculate `refugees_per_1k_pop` for every year.

```r
(df_enriched %>%
  group_by(coo_name) %>%
  summarize(n_years = sum(refugees_per_1k_pop > 0, na.rm=T)) %>%
  filter(n_years == 13))$coo_name -> coo_to_keep_2

df_enriched %>%
  filter(coo_name %in% coo_to_keep_2)-> df_enriched_clean
```


Next, I'll use 2010 as a baseline year, and subtract each year's value from that. This will allow me to measure change over time from this common baseline, and compare nations in terms of a normalized change.

```r
df_enriched_clean %>%
  filter(year == 2010) %>%
  group_by(coo_name) %>%
  summarize(baseline_refugees_per_1k_pop = sum(refugees)/(first(pop)/1000)) -> baseline_year

df_enriched_clean %>%
  left_join(baseline_year, by='coo_name') %>%
  mutate(change_from_baseline = refugees_per_1k_pop - baseline_refugees_per_1k_pop) -> df_enriched_clean

df_enriched_clean %>%
  head()
```

# Identifying regions of interest

Next, I want to identify a smaller set of "interesting" COOs that have experienced large increases over the baseline. I'll identify an upper bound percentile of max change over baseline, and then I'll use a value that approximates that as a filter. This gives me 4 "interesting" nations.

```r
df_enriched_clean %>%
  group_by(coo_name) %>%
  summarize(max_change_from_baseline = max(change_from_baseline)) %>%
  summarize(p90_change = quantile(max_change_from_baseline, .975, na.rm=T))


df_enriched_clean %>%
  group_by(coo_name, coo_iso) %>%
  summarize(max_change_from_baseline = max(change_from_baseline),
            last_value = last(change_from_baseline, order_by=year)) %>%
  filter(max_change_from_baseline > 32) -> coos_with_large_changes_over_baseline

coos_with_large_changes_over_baseline
```

# Data visualization

Finally, I'll plot change over the 2010 baseline (in refugees per 1k population), and highlight the 4 interesting nations identified above.

I'll use this to help me pick colors for the `ggtitle` text.

```r
scales::show_col(scales::hue_pal()(4))
```

```r
df_enriched_clean %>%
  mutate(class = coo_name %in% coos_with_large_changes_over_baseline$coo_name,
         year = as.Date(paste0(as.character(year), '-01-01'))) %>%
  arrange(year, desc(class)) %>%
  mutate(coo_iso = fct_inorder(coo_iso)) %>%
  ggplot(aes(x=year, y=change_from_baseline, color=coo_iso)) +
    geom_line() +
    scale_x_date(date_labels="%Y", date_breaks="1 year") +
    ggthemes::theme_solarized() +
    gghighlight::gghighlight(class == TRUE) +
    ggtitle("<strong><span style='color:#00BFC4'>SYR</span></strong>, <strong><span style='color:#C77CFF'>UKR</span></strong>, <strong><span style='color:#F8766D'>CAF</span></strong>, and <strong><span style='color:#7CAE00'>ERI</span></strong> experienced large increases in<br>normalized refugee outflow (i.e., refugees per 1k population),<br> compared to their 2010 baseline.") +
    xlab('Year') +
    ylab('Change in Normalized Refugee Outflow*') +
    labs(caption = "<span style='font-size:7pt'>*Change in refugees per 1k population from the baseline value observed in 2010.</span>") +
    theme(plot.title = ggtext::element_markdown(),
          plot.caption = ggtext::element_markdown()) -> plot
plot
```