export type Framework = "pytorch" | "paddle";

export interface FieldSpec {
  key: string;
  label: string;
  type: "int" | "float" | "bool" | "int_list" | "enum" | "text";
  default: unknown;
  help: string;
  minimum?: number | null;
  maximum?: number | null;
  step?: number | null;
  options?: string[] | null;
}

export interface CatalogPort {
  name: string;
  required: boolean;
  data_type: "Tensor" | "ScalarBool" | "ScalarInt";
  role?: string | null;
  call_arg?: string | null;
  output_index: number;
}

export interface BlockSpec {
  op: string;
  label: string;
  category: string;
  description: string;
  color: string;
  torch_name?: string | null;
  paddle_name?: string | null;
  torch_api?: string | null;
  paddle_api?: string | null;
  input_mode: "single" | "merge";
  control_type?: "if" | "for" | "while" | null;
  output_data_type: "Tensor" | "ScalarBool" | "ScalarInt";
  input_ports: CatalogPort[];
  output_ports: CatalogPort[];
  pytorch_only: boolean;
  fields: FieldSpec[];
  system: boolean;
}

export interface CatalogResponse {
  version: string;
  blocks: BlockSpec[];
}

export interface Position {
  x: number;
  y: number;
}

export interface GraphNode {
  id: string;
  op: string;
  params: Record<string, unknown>;
  teaching_note: string;
  composite_ref?: CompositeRef | null;
  param_overrides?: Record<string, unknown>;
  region_refs?: Record<string, string>;
  state_contract?: StateContract | null;
}

export interface EdgeEndpoint {
  node_id: string;
  port: string;
}

export interface GraphEdge {
  id: string;
  source: EdgeEndpoint;
  target: EdgeEndpoint;
}

export interface GraphMeta {
  name: string;
  author: string;
  is_composite: boolean;
  composite_version_tag: string | null;
  note: string;
  updated_at: string;
}

export interface IRDocument {
  ir_version: "0.2" | "0.3";
  target_framework: Framework;
  graph_meta: GraphMeta;
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  regions?: Record<string, GraphRegion>;
  resources?: CompositeResource[];
  ui: {
    positions: Record<string, Position>;
    zoom: number;
  };
  check_info?: {
    static_shape_pass: boolean;
    error_count: number;
    checked_at?: string | null;
  } | null;
}

export interface PortContract {
  name: string;
  data_type: "Tensor" | "ScalarBool" | "ScalarInt";
  shape?: Array<number | null> | null;
  dtype?: string | null;
  required: boolean;
  role?: string | null;
}

export interface StateContract {
  inputs: PortContract[];
  outputs: PortContract[];
}

export interface CompositeRef {
  resource_id: string;
  revision: number;
}

export interface GraphRegion {
  id: string;
  kind: "composite" | "predicate" | "then" | "else" | "body";
  graph: IRDocument["graph"];
  ui: IRDocument["ui"];
  inputs: PortContract[];
  outputs: PortContract[];
  read_only: boolean;
}

export interface CompositeResource {
  schema_version: "1.0";
  resource_id: string;
  name: string;
  revision: number;
  description: string;
  author: string;
  created_at: string;
  graph: IRDocument["graph"];
  regions: Record<string, GraphRegion>;
  ui: IRDocument["ui"];
  inputs: PortContract[];
  outputs: PortContract[];
  dependencies: CompositeResource[];
  parameter_defaults: Record<string, unknown>;
}

export interface CompositeValidateResponse {
  valid: boolean;
  resource?: CompositeResource | null;
  diagnostics: Diagnostic[];
  parameter_count: number;
}

export interface MojoAsset {
  id: string;
  name: string;
  createdAt: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  positions: Record<string, Position>;
}

export interface Diagnostic {
  code: string;
  severity: "error" | "warning" | "info";
  node_id?: string | null;
  edge_id?: string | null;
  field?: string | null;
  message: string;
  teaching_tip: string;
}

export interface PortInfo {
  name: string;
  io: "in" | "out";
  data_type: string;
  role?: string | null;
  shape?: Array<number | null> | null;
  dtype?: string | null;
}

export interface NodeAnalysis {
  node_id: string;
  label: string;
  ports: PortInfo[];
}

export interface AnalysisResult {
  valid: boolean;
  normalized_ir: IRDocument | null;
  nodes: NodeAnalysis[];
  diagnostics: Diagnostic[];
  chain_count: number;
}

export interface TraceStep {
  index: number;
  node_id: string;
  label: string;
  input_shape?: Array<number | null> | null;
  input_shapes?: Array<Array<number | null>> | null;
  output_shape?: Array<number | null> | null;
  dtype?: string | null;
  note: string;
}

export interface TraceResponse {
  mode: "structure_preview";
  message: string;
  steps: TraceStep[];
  diagnostics: Diagnostic[];
}

export interface Moment {
  id: string;
  world: "python" | "turtle" | "netbrick";
  kind: string;
  concepts: string[];
  severity: "info" | "warning" | "error";
  importance: number;
  step_index?: number | null;
  node_id?: string | null;
  line?: number | null;
  source_ref?: Record<string, unknown> | null;
  label: string;
  why: string;
  question?: string | null;
  evidence: Array<Record<string, unknown>>;
  expected?: unknown;
  actual?: unknown;
  tags: string[];
  confidence: number;
  enriched: boolean;
}

export interface CodegenResponse {
  filename: string;
  source: string;
  syntax_valid: boolean;
  warnings: Diagnostic[];
}

export interface SampleSummary {
  id: string;
  title: string;
  description: string;
}

export interface ImportResponse {
  ir: IRDocument | null;
  diagnostics: Diagnostic[];
}

export interface CourseStep {
  title: string;
  markdown: string;
  focus_node_ids: string[];
}

export type BottomPanel = "diagnostics" | "code" | "trace";
