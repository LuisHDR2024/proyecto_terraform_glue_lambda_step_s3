# =====================================================
# basicos para arrancar glue
# =====================================================

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Contextos
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Recibir parametros desde step fuctions
args = getResolvedOptions(sys.argv, ['JOB_NAME','input_path','output_path', 'reject_path'])

job_name = args['JOB_NAME']
input_path = args['input_path']
output_path = args['output_path']
reject_path = args['reject_path']

# Inicializar job
job = Job(glueContext)
job.init(job_name, args)

# =====================================================
# iniciar proceso ETL
# =====================================================

from pyspark.sql.functions import col, regexp_extract, regexp_replace

# Leer CSV
mydf = spark.read \
    .option("header", True) \
    .option("inferSchema", False) \
    .option("escape", '"') \
    .option("multiLine", True) \
    .option("mode", "PERMISSIVE") \
    .option("encoding", "UTF-8") \
    .csv(input_path)

# forzar nombres estandar para columnas
columnas_standar = [
    "row_id","order_id","order_date","ship_date","ship_mode",
    "customer_id","customer_name","segment","country","city",
    "state","postal_code","region","product_id","category",
    "sub_category","product_name","sales","quantity","discount","profit"
]
mydf = mydf.toDF(*columnas_standar)

from pyspark.sql.functions import col
from pyspark.sql.types import *

# forzar un casteo estandar

tipos = {
    "row_id": IntegerType(),
    "order_id": StringType(),
    "order_date": StringType(), # luego formatear
    "ship_date": StringType(),  # luego formatear
    "ship_mode": StringType(),
    "customer_id": StringType(),
    "customer_name": StringType(),
    "segment": StringType(),
    "country": StringType(),
    "city": StringType(),
    "state": StringType(),
    "postal_code": StringType(),
    "region": StringType(),
    "product_id": StringType(),
    "category": StringType(),
    "sub_category": StringType(),
    "product_name": StringType(),
    "sales": DoubleType(),
    "quantity": IntegerType(),
    "discount": DoubleType(),
    "profit": DoubleType()
}

mydf = mydf.select([col(c).cast(t).alias(c) for c, t in tipos.items()])

# aplicar formato fecha por separado
from pyspark.sql.functions import to_date
mydf = mydf.withColumn("order_date", to_date(col("order_date"), "M/d/yyyy"))
mydf = mydf.withColumn("ship_date",  to_date(col("ship_date"),  "M/d/yyyy"))

# ===== reglas de validacion categoricas
ship_modes_valids = ['Second Class', 'Standard Class', 'First Class', 'Same Day']
region_valids     = ['South', 'West', 'Central', 'East']
category_valids   = ['Furniture', 'Office Supplies', 'Technology']

# ===== reglas numericas
numeric_rules = {
    "sales":    {"lower": 0,     "upper": 5000},
    "quantity": {"lower": 1,     "upper": 20  },
    "discount": {"lower": 0.0,   "upper": 0.9  },
    "profit":   {"lower": -2000, "upper": 2000 },
}

# establecer filtros categoricos
order_id_filter      = col("order_id").rlike("^[A-Z]{2}-\\d{4}-\\d{6}$")
order_date_filter    = col("order_date").isNotNull()
ship_date_filter     = col("ship_date").isNotNull()
ship_modes_filter    = col("ship_mode").isin(ship_modes_valids)
customer_id_filter   = col("customer_id").rlike(r"^[A-Za-z]{2}-\d{5}$")
customer_name_filter = col("customer_name").isNotNull()
country_filter       = col("country").isNotNull()
city_filter          = col("city").isNotNull()
state_filter         = col("state").isNotNull()
region_filter        = col("region").isin(region_valids)
product_id_filter    = col("product_id").rlike(r"^[A-Z]{2,3}-[A-Z]{2,3}-\d{8}$")
category_filter      = col("category").isin(category_valids)
sub_category_filter  = col("sub_category").isNotNull()
postal_code_filter   = col("postal_code").isNotNull()

# establecer filtros numericos
sales_filter    = col("sales").between(numeric_rules["sales"]["lower"],      numeric_rules["sales"]["upper"])
quantity_filter = col("quantity").between(numeric_rules["quantity"]["lower"],numeric_rules["quantity"]["upper"])
discount_filter = col("discount").between(numeric_rules["discount"]["lower"],numeric_rules["discount"]["upper"])
profit_filter   = col("profit").between(numeric_rules["profit"]["lower"],    numeric_rules["profit"]["upper"])

# preparar filtros
filtro_final = (
    order_id_filter      &
    order_date_filter    &
    ship_date_filter     &
    ship_modes_filter    &
    customer_id_filter   &
    customer_name_filter &
    country_filter       &
    city_filter          &
    state_filter         &
    region_filter        &
    product_id_filter    &
    category_filter      &
    sub_category_filter  &
    postal_code_filter   &
    sales_filter         &
    quantity_filter      &
    discount_filter      &
    profit_filter
)

mydf_reject = mydf.filter(~filtro_final)
mydf        = mydf.filter(filtro_final)

# ===== escritura
mydf.write \
    .format("parquet") \
    .mode("overwrite") \
    .save(output_path)

mydf_reject.write \
    .format("parquet") \
    .mode("overwrite") \
    .save(reject_path)

# Finalizar job
job.commit()
