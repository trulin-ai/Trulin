
import React, { useState } from 'react';
import {
  Database,
  HardDrive,
  Workflow,
  GitBranch,
  Radio,
  FileCode2,
  BarChart3,
  ShieldCheck,
  Briefcase,
  Cpu,
  Server
} from 'lucide-react';

/*
 * Iconify icon names:
 * logos:    official product / technology logo collection
 * simple-icons: brand logo collection
 *
 * A shared vendor icon is used where no distinct product logo
 * is available in the icon collections.
 */

const CATEGORY_STYLE = {
  database: {
    bg: '#EFF6FF',
    border: '#BFDBFE',
    color: '#2563EB',
    Icon: Database
  },
  storage: {
    bg: '#ECFEFF',
    border: '#A5F3FC',
    color: '#0891B2',
    Icon: HardDrive
  },
  etl: {
    bg: '#F0FDF4',
    border: '#BBF7D0',
    color: '#16A34A',
    Icon: Workflow
  },
  orchestration: {
    bg: '#FAF5FF',
    border: '#E9D5FF',
    color: '#9333EA',
    Icon: GitBranch
  },
  messaging: {
    bg: '#FFF7ED',
    border: '#FED7AA',
    color: '#EA580C',
    Icon: Radio
  },
  schema: {
    bg: '#EEF2FF',
    border: '#C7D2FE',
    color: '#4F46E5',
    Icon: FileCode2
  },
  bi: {
    bg: '#FEFCE8',
    border: '#FEF08A',
    color: '#CA8A04',
    Icon: BarChart3
  },
  governance: {
    bg: '#FEF2F2',
    border: '#FECACA',
    color: '#DC2626',
    Icon: ShieldCheck
  },
  crm_erp: {
    bg: '#F0F9FF',
    border: '#BAE6FD',
    color: '#0284C7',
    Icon: Briefcase
  },
  ml_ai: {
    bg: '#FDF4FF',
    border: '#F5D0FE',
    color: '#C026D3',
    Icon: Cpu
  }
};

/*
 * Complete 108 connector ID mapping.
 *
 * Format:
 * connector_id: [preferred_icon, vendor_fallback]
 *
 * These are Iconify collection identifiers, not custom SVGs.
 */

const CONNECTOR_LOGOS = {

  // DATABASES

  alloydb: ['logos:google-cloud', 'logos:google-cloud'],
  athena: ['logos:aws-athena', 'logos:aws'],
  documentdb: ['logos:aws-documentdb', 'logos:aws'],
  dynamodb: ['logos:aws-dynamodb', 'logos:aws'],
  clickhouse: ['simple-icons:clickhouse', 'logos:clickhouse'],
  cloud_sql_postgres: ['logos:google-cloud', 'logos:google-cloud'],
  cloudera_impala: ['simple-icons:cloudera', 'logos:cloudera'],
  cratedb: ['simple-icons:cratedb', 'logos:cratedb'],
  datastax: ['simple-icons:datastax', 'logos:datastax'],
  databricks: ['simple-icons:databricks', 'logos:databricks'],
  hive: ['simple-icons:apachehive', 'logos:apache-hive'],
  azure_cosmos_db: ['logos:azure', 'logos:azure'],
  azure_cosmos_nosql: ['logos:azure', 'logos:azure'],
  mssql: ['simple-icons:microsoftsqlserver', 'logos:microsoft'],
  mongodb_self: ['simple-icons:mongodb', 'logos:mongodb'],
  mongodb_atlas: ['simple-icons:mongodb', 'logos:mongodb'],
  mysql: ['simple-icons:mysql', 'logos:mysql'],
  on_prem_databases: [null, null],
  oracle: ['simple-icons:oracle', 'logos:oracle'],
  postgresql: ['simple-icons:postgresql', 'logos:postgresql'],
  prestosql: ['simple-icons:prestodb', 'logos:presto'],
  sap_ase: ['simple-icons:sap', 'logos:sap'],
  sap_hana: ['simple-icons:sap', 'logos:sap'],
  starburst: ['simple-icons:starburst', 'logos:starburst'],
  teradata: ['simple-icons:teradata', 'logos:teradata'],
  trino: ['simple-icons:trino', 'logos:trino'],

  // STORAGE AND WAREHOUSES

  redshift: ['logos:aws-redshift', 'logos:aws'],
  s3: ['logos:aws-s3', 'logos:aws'],
  dremio: ['simple-icons:dremio', 'logos:dremio'],
  bigquery: ['logos:google-bigquery', 'logos:google-cloud'],
  gcs: ['logos:google-cloud', 'logos:google-cloud'],
  iceberg: ['simple-icons:apacheiceberg', 'logos:apache'],
  synapse: ['logos:azure', 'logos:microsoft'],
  sap_datasphere: ['simple-icons:sap', 'logos:sap'],
  snowflake: ['simple-icons:snowflake', 'logos:snowflake'],

  // ETL

  aws_glue: ['logos:aws-glue', 'logos:aws'],
  alteryx: ['simple-icons:alteryx', 'logos:alteryx'],
  coalesce: ['simple-icons:coalesce', 'logos:coalesce'],
  fivetran: ['simple-icons:fivetran', 'logos:fivetran'],
  hightouch: ['simple-icons:hightouch', 'logos:hightouch'],
  informatica_cdi: ['simple-icons:informatica', 'logos:informatica'],
  informatica_powercenter: ['simple-icons:informatica', 'logos:informatica'],
  matillion: ['simple-icons:matillion', 'logos:matillion'],
  azure_data_factory: ['logos:azure', 'logos:microsoft'],
  ssis: ['simple-icons:microsoftsqlserver', 'logos:microsoft'],
  talend: ['simple-icons:talend', 'logos:talend'],
  dbt: ['simple-icons:dbt', 'logos:dbt'],

  // ORCHESTRATION

  mwaa_openlineage: ['logos:aws', 'logos:aws'],
  airflow_openlineage: ['simple-icons:apacheairflow', 'logos:apache-airflow'],
  flink_openlineage: ['simple-icons:apacheflink', 'logos:apache-flink'],
  spark_openlineage: ['simple-icons:apachespark', 'logos:apache-spark'],
  astronomer_openlineage: ['simple-icons:astronomer', 'logos:astronomer'],
  dagster: ['simple-icons:dagster', 'logos:dagster'],
  generic_openlineage: ['simple-icons:openlineage', 'logos:openlineage'],
  cloud_composer_openlineage: ['logos:google-cloud', 'logos:google-cloud'],
  dataflow: ['logos:google-cloud', 'logos:google-cloud'],

  // MESSAGING AND SCHEMA

  aiven_kafka: ['simple-icons:aiven', 'logos:aiven'],
  amazon_msk: ['logos:aws-msk', 'logos:aws'],
  apache_kafka: ['simple-icons:apachekafka', 'logos:apache-kafka'],
  confluent_kafka: ['simple-icons:confluent', 'logos:confluent'],
  azure_event_hubs: ['logos:azure', 'logos:microsoft'],
  redpanda_kafka: ['simple-icons:redpanda', 'logos:redpanda'],
  confluent_schema_registry: ['simple-icons:confluent', 'logos:confluent'],

  // BUSINESS INTELLIGENCE

  quicksight: ['logos:aws-quicksight', 'logos:aws'],
  anaplan: ['simple-icons:anaplan', 'logos:anaplan'],
  domo: ['simple-icons:domo', 'logos:domo'],
  cognos: ['simple-icons:ibm', 'logos:ibm'],
  looker: ['simple-icons:looker', 'logos:looker'],
  metabase: ['simple-icons:metabase', 'logos:metabase'],
  microstrategy: ['simple-icons:microstrategy', 'logos:microstrategy'],
  ms_fabric: ['simple-icons:microsoft', 'logos:microsoft'],
  power_bi: ['simple-icons:powerbi', 'logos:microsoft'],
  ssrs: ['simple-icons:microsoftsqlserver', 'logos:microsoft'],
  mode: ['simple-icons:mode', 'logos:mode'],
  omni: ['simple-icons:omni', 'logos:omni'],
  qlik_sense_cloud: ['simple-icons:qlik', 'logos:qlik'],
  qlik_sense_enterprise: ['simple-icons:qlik', 'logos:qlik'],
  redash: ['simple-icons:redash', 'logos:redash'],
  sigma: ['simple-icons:sigma', 'logos:sigma'],
  sisense: ['simple-icons:sisense', 'logos:sisense'],
  tableau: ['simple-icons:tableau', 'logos:tableau'],
  thoughtspot: ['simple-icons:thoughtspot', 'logos:thoughtspot'],

  // GOVERNANCE

  altr: ['simple-icons:altr', null],
  sagemaker_unified_studio: ['logos:aws-sagemaker', 'logos:aws'],
  anomalo: ['simple-icons:anomalo', null],
  ataccama: ['simple-icons:ataccama', null],
  bigid: ['simple-icons:bigid', null],
  bigeye: ['simple-icons:bigeye', null],
  cyera: ['simple-icons:cyera', null],
  elementary: ['simple-icons:elementary', null],
  google_knowledge_catalog: ['logos:google-cloud', 'logos:google-cloud'],
  immuta: ['simple-icons:immuta', null],
  monte_carlo: ['simple-icons:montecarlodata', null],
  qualytics: ['simple-icons:qualytics', null],
  soda: ['simple-icons:soda', null],
  telmai: ['simple-icons:telmai', null],

  // CRM AND ERP

  glean: ['simple-icons:glean', null],
  netsuite: ['simple-icons:oracle', 'logos:oracle'],
  salesforce: ['simple-icons:salesforce', 'logos:salesforce'],
  sap_bw_4hana: ['simple-icons:sap', 'logos:sap'],
  sap_ecc: ['simple-icons:sap', 'logos:sap'],
  sap_s4hana: ['simple-icons:sap', 'logos:sap'],
  confluence: ['simple-icons:confluence', 'logos:atlassian'],
  jira: ['simple-icons:jira', 'logos:atlassian'],
  github: ['simple-icons:github', 'logos:github'],
  slack: ['simple-icons:slack', 'logos:slack'],

  // ML AND AI

  sagemaker: ['logos:aws-sagemaker', 'logos:aws'],
  sagemaker_studio_ml: ['logos:aws-sagemaker', 'logos:aws']
};

/*
 * Final fallback for unknown connector IDs.
 * This does not invent a connector logo.
 */

function CategoryFallback({ category, size }) {
  const style = CATEGORY_STYLE[category] || {
    bg: '#F1F5F9',
    border: '#CBD5E1',
    color: '#475569',
    Icon: Server
  };

  const IconComponent = style.Icon;

  return (
    <div
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: 8,
        background: style.bg,
        border: `1px solid ${style.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}
    >
      <IconComponent
        size={Math.round(size * 0.56)}
        color={style.color}
        strokeWidth={1.8}
      />
    </div>
  );
}

/*
 * Icon URL helper.
 */

function getIconUrl(iconName) {
  if (!iconName) return null;

  return `https://api.iconify.design/${iconName.replace(':', '/')}.svg`;
}

/*
 * Main connector icon component.
 */

export default function ConnectorIcon({
  connector,
  size = 34
}) {
  const id = String(connector?.id || '').toLowerCase();
  const name = String(connector?.name || '');
  const category = String(connector?.category || '').toLowerCase();

  const mapping = CONNECTOR_LOGOS[id];

  const candidates = mapping
    ? [...new Set(mapping.filter(Boolean).map(getIconUrl))]
    : [];

  const [failed, setFailed] = useState({
    id: '',
    count: 0
  });

  const failedCount = failed.id === id ? failed.count : 0;
  const currentUrl = candidates[failedCount];

  const handleError = () => {
    setFailed(previous => ({
      id,
      count: Math.min(
        previous.id === id ? previous.count + 1 : 1,
        candidates.length
      )
    }));
  };

  if (!currentUrl) {
    return (
      <CategoryFallback
        category={category}
        size={size}
      />
    );
  }

  return (
    <div
      title={name}
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: 8,
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        overflow: 'hidden'
      }}
    >
      <img
        key={`${id}-${currentUrl}`}
        src={currentUrl}
        alt={`${name} logo`}
        width={Math.round(size * 0.76)}
        height={Math.round(size * 0.76)}
        loading="lazy"
        onError={handleError}
        style={{
          objectFit: 'contain',
          display: 'block',
          maxWidth: '100%',
          maxHeight: '100%'
        }}
      />
    </div>
  );
}