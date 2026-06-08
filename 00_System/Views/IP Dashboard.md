# IP Dashboard

## Active Ideas

```dataview
TABLE status, priority, updated
FROM "10_IP/Ideas"
SORT updated DESC
```

## Scripts

```dataview
TABLE status, platform, updated
FROM "10_IP/Scripts"
SORT updated DESC
```

## Publish Records

```dataview
TABLE status, channel, updated
FROM "20_Content/Publish"
SORT updated DESC
```
