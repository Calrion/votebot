# votebot

## What is this?

The world will love bots until they take over. Until then, we'll keep making them! `votebot` is a bot for [Slack](https://slack.com/)
which allows you to ... well, vote! `votebot` is built using Python on AWS Lambda and driven by the Outgoing Webhook
integration in Slack. 

## Under the hood

The options for `votebot` are stored in a DynamoDB table for persistence between Lambda function runs. The hash key is 
titled `selection`, and a second attribute called `options` stores each votable option. They are stored as comma-separated
values. There is a another attribute, `icon_emoji`, which allows you to customize the reaction emoji that users
can click on. For each option, the following convention is used:

```
Title / description1 / description2 / description3,
```

An example of what your DynamoDB table might look like is as follows:

| Hash key | options attribute | icon_emoji attribute | 
| -------- | ----------------- | -------------------- |
| pistarro | Pepperoni / tomato sauce / pepperoni / mozzarella / basil, Florintina / spinach / ricotta / artichoke / roasted pepper / parmesan v. | pizza |

## Dependencies

### Python libraries

- boto3
- slacker

### AWS services

- Lambda
- API Gateway
- DynamoDB
- IAM

### Slack services

- Outgoing Webhooks
- Bot integration

## Example

```
wayne: votebot open pistarro

[11:07] votebotBOT: @here wayne has opened voting for `pistarro`. Please vote by clicking on an emoji! To close voting, please enter `votebot close pistarro-10/15/2015-15:07:13`

[11:07] votebotBOT: Margherita tomato sauce / mozzarella / basil v.
:pizza:2  

[11:07] votebotBOT: Bianca garlic / caramelized onions / ricotta / mozzarella / pecorino v.
:pizza:4  

[11:07] votebotBOT: Capricciosa tomato sauce / mushroom / artichoke / speck / mozzarella
:pizza:1  

[11:07] votebotBOT: Versace tomato sauce / mozzarella / prosciutto / arugula
:pizza:1  

[11:07] votebotBOT: Pepperoni tomato sauce / pepperoni / mozzarella / basil
:pizza:3 :gopherhead:2  

...

wayne: votebot close pistarro-10/15/2015-15:07:13

[11:20] votebotBOT: @here wayne closed voting for pistarro-10/15/2015-15:07:13! Results:
3 vote(s) each for Bianca, Pepperoni, Florintina
2 vote(s) each for Diavola, Blu Fico, Salsiccia, Carciofo 
1 vote(s) each for Margherita, Napoletana, Fumo Verde, Polpettine, Bresaola, Marinara (no cheese)  
0 vote(s) each for Capricciosa, Versace, Funghi, Donatello, Maiale, Ananas, Verdure 
Total votes: 23
```

## Setup

### tl;dr

1. Clone this votebot repo
1. Set up an Outgoing Webhook and bot integration in Slack
1. Place your channel token in a file named `SLACK_CHANNEL_TOKEN` at this level in the directory
1. Place your bot authorization token in a file named `SLACK_BOT_API_TOKEN` at this level in the directory
1. Set up IAM permissions for Lambda
1. Set up DynamoDB
1. Populate the `vote-options` table with some things you want to vote on (remember, options are comma-separated)
1. Zip the contents of the `votebot` directory, *NOT* the directory itself
1. Create a Lambda function by uploading the zip file to Lambda
1. Create an API Gateway entry pointing to your Lambda function, ensuring you include a mapping template
1. Once deployed, copy the POST URL of your API Gateway entry and configure your Outgoing Webhook with it
1. Vote!

### The longer version

#### DynamoDB

There are two DynamoDB tables `votebot` uses. One is called `vote-options` and the other is `vote-open`.
The vote storage tables use 1 provisioned read and 1 provisioned write throughput, along with a small
amount of actual storage. This falls well below the free tier for DDB (25 reads and 25 writes per second).
If you are already a heavy DDB user and exceed the free tier, the tables will cost about ~$1 per month.

To set up DynamoDB, run setup_ddb.sh. For now, the table must be manually populated with options.

#### IAM

The IAM role must have a trust relationship for Lambda which meets the following:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

And the policy is expressed as:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:*"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-west-2:*:table/vote-options",
                "arn:aws:dynamodb:us-west-2:*:table/vote-open"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

To set up IAM, run setup_iam.sh. The role will be named `votebot`.

## More information

See the [Fugue blog](https://blog.fugue.co/2015-10-15-votebot.html) for a walkthrough of setup, packaging, and deployment!
