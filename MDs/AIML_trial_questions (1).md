# AI/ML trial questions 

## Task 1: Internal Policy Question-Answering Assistant 

Build an AI assistant that answers employee questions using only the policy documents provided to you. 

The assistant should: 

Retrieve the relevant information from the documents. 

- Provide a clear and accurate answer. 

- Mention the source document and relevant page or section. 

- Prefer the latest approved policy when multiple versions exist. 

- Ignore documents marked as draft, expired, or outdated. 

- Clearly state when the available documents do not contain enough information to answer a question. 

Handle conflicting policies appropriately. 

You may use any programming language, framework, embedding model, vector database, or LLM. 

Links : 

- ��> <u>https://www.iima.ac.in/sites/default/files/2024] 01/HR%20Policy%20Manual%202024.pdf</u> 

- ��> <u>https://github.com/wasiahmad/PolicyQA</u> 

- ��> <u>https://github.com/AbhilashaRavichander/PrivacyQA_EMNLP</u> 

### Deliverables 

Working application or API. 

- Source code with setup instructions. 

- A small evaluation set containing answerable, unanswerable, and conflictingpolicy questions. 

AI/ML trial questions 

1 

- A short explanation of your architecture, document chunking, retrieval approach, and evaluation method. 

- Examples of incorrect answers or limitations you observed. 

## Task 2: Demand Forecasting with Business Costs 

Using the provided historical sales dataset, build a system that forecasts product demand for the next 14 days and recommends inventory order quantities. 

Different products have different: 

- Understock costs. 

- Overstock costs. 

- Pack sizes. 

- Maximum order limits. 

Your objective is not only to reduce forecasting error, but also to minimize the total business cost caused by ordering too much or too little inventory. 

The solution should: 

- Explore trends, seasonality, missing values, and unusual sales periods. 

- Create a simple forecasting baseline. 

- Build and compare an improved forecasting approach. 

- Use time-based validation or rolling backtesting. 

- Generate 14-day demand forecasts. 

- Convert forecasts into valid order quantities while respecting pack sizes and order limits. 

Compare solutions using forecasting metrics and total business cost. 

- Analyze products where the model performs poorly. 

Links : 

- ��> <u>https://www.kaggle.com/competitions/store-sales-time-seriesforecasting/data</u> 

AI/ML trial questions 

2 

### Deliverables 

- Working source code or notebook. 

- Forecasts and recommended order quantities. 

- Baseline and improved-model comparison. 

- MAE, forecast bias, understock units, overstock units, and total business cost. 

- Setup instructions and a short explanation of your approach. 

- A brief monitoring and retraining plan for production use. 

AI/ML trial questions 

3 

