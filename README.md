# Dice Template FeatureCloud App

## Description
A Dice FeautureCloud app, allowing the computation of a federated mean of dice throwings. This repository can be used as a template repository and is a good starting point for you own implementations.
- Each participant rolls a die and sends its result to the coordinator
- The coordinator adds all numbers and sends the sum back to the participants

## Input
No input needed.

## Output
- output.csv containing the global mean

## Workflows
Does not support any other apps to be executed in a workflow. This app is only available to support developers in their own implementations.

## Config
Use the config file to customize your training. Just upload it together with your training data as `config.yml`

```
fc_dice:
  output_name: 'output.csv'
```