// API types derived from webapp/models/schemas.py

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface ChapterResponse {
  id: number;
  chapter_number: number;
  title: string | null;
  status: string;
  audio_path: string | null;
  audio_duration: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string; // pending, running, completed, failed
  progress: number | null;
  message: string | null;
  result: Record<string, unknown> | null;
  words_generated: number | null;
  estimated_total_words: number | null;
}

export interface StoryResponse {
  id: number;
  title: string;
  description: string | null;
  prompt: string | null;
  language: string | null;
  world_id: number | null;
  world_name: string | null;
  status: string;
  visibility: string;
  share_code: string | null;
  upvotes: number;
  downvotes: number;
  created_at: string;
  updated_at: string;
  chapters: ChapterResponse[];
  active_task: TaskStatusResponse | null;
}

export interface StoryListResponse {
  id: number;
  title: string;
  description: string | null;
  language: string | null;
  world_id: number | null;
  world_name: string | null;
  status: string;
  visibility: string;
  chapter_count: number;
  created_at: string;
}

export interface PublicStoryListItem {
  id: number;
  title: string;
  description: string | null;
  language: string | null;
  world_id: number | null;
  world_name: string | null;
  status: string;
  chapter_count: number;
  upvotes: number;
  downvotes: number;
  created_at: string;
  owner_name: string;
}

export interface PublicStoryResponse {
  id: number;
  title: string;
  description: string | null;
  prompt: string | null;
  language: string | null;
  status: string;
  visibility: string;
  share_code: string | null;
  upvotes: number;
  downvotes: number;
  user_vote: string | null;
  is_bookmarked: boolean;
  created_at: string;
  chapters: ChapterResponse[];
  owner_name: string;
}

export interface BookmarkResponse {
  bookmarked: boolean;
}

export interface BookmarkedStoryListItem {
  id: number;
  title: string;
  description: string | null;
  language: string | null;
  status: string;
  chapter_count: number;
  upvotes: number;
  downvotes: number;
  created_at: string;
  owner_name: string;
  bookmarked_at: string;
}

export interface VoteRequest {
  vote_type: string | null;
}

export interface ReportRequest {
  reason: string;
}

export interface ShareLinkResponse {
  share_code: string;
  share_url: string;
}

export interface ApiKeysUpdate {
  openai_api_key?: string | null;
  elevenlabs_api_key?: string | null;
}

export interface ApiKeysStatus {
  has_openai_key: boolean;
  has_elevenlabs_key: boolean;
  free_stories_used: number;
  free_stories_limit: number;
}

export interface BudgetStatus {
  total_budget: number;
  total_spent: number;
  free_stories_generated: number;
  free_stories_per_user: number;
}

export interface WorldCreate {
  name: string;
  description?: string | null;
  prompt_template?: string | null;
  characters?: Record<string, string> | null;
  valid_speakers?: string[] | null;
  voice_config?: Record<string, Record<string, unknown>> | null;
  visibility?: string;
}

export interface WorldUpdate {
  name?: string | null;
  description?: string | null;
  prompt_template?: string | null;
  characters?: Record<string, string> | null;
  valid_speakers?: string[] | null;
  voice_config?: Record<string, Record<string, unknown>> | null;
  visibility?: string | null;
}

export interface WorldResponse {
  id: number;
  name: string;
  description: string | null;
  is_builtin: boolean;
  prompt_template: string | null;
  characters: Record<string, string> | null;
  valid_speakers: string[] | null;
  voice_config: Record<string, Record<string, unknown>> | null;
  visibility: string;
  share_code: string | null;
  story_count: number;
  owner_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorldListItem {
  id: number;
  name: string;
  description: string | null;
  is_builtin: boolean;
  visibility: string;
  story_count: number;
  owner_name: string | null;
  created_at: string;
}

export interface VoiceListItem {
  voice_id: string;
  name: string;
  category: string;
  labels: Record<string, string>;
  preview_url: string;
}

export interface VoiceSettings {
  voice_id: string;
  stability?: number;
  similarity_boost?: number;
  style?: number;
}

export interface VoiceConfigResponse {
  speakers: string[];
  voice_config: Record<string, VoiceSettings>;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface StoryCreate {
  title: string;
  description?: string | null;
  prompt?: string | null;
  num_chapters?: number;
  language?: string | null;
  world_id?: number | null;
  config_override?: Record<string, unknown> | null;
}

export interface GenerateAudioRequest {
  story_id: number;
  chapter_numbers?: number[] | null;
  voice_override?: Record<string, Record<string, unknown>> | null;
}
