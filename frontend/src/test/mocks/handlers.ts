import { http, HttpResponse } from 'msw'
import type {
  User,
  ApiKeysStatus,
  BudgetStatus,
  PublicStoryListItem,
  WorldResponse,
  BookmarkedStoryListItem,
  StoryResponse,
  VoiceListItem,
  VoiceConfigResponse,
  LoginResponse,
  TaskStatusResponse,
} from '../../types'

const BASE = 'http://localhost:5173/api'

const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  is_active: true,
  created_at: '2024-01-01T00:00:00',
}

const mockApiKeysStatus: ApiKeysStatus = {
  has_openai_key: false,
  has_elevenlabs_key: false,
  free_stories_used: 0,
  free_stories_limit: 20,
  free_audio_used: 0,
  free_audio_limit: 5,
}

const mockBudget: BudgetStatus = {
  total_budget: 50.0,
  total_spent: 5.0,
  free_stories_generated: 10,
  free_stories_per_user: 20,
}

const mockStory: PublicStoryListItem = {
  id: 1,
  title: 'Test Story',
  description: 'A test story',
  language: 'Persian (Farsi)',
  world_id: null,
  world_name: null,
  status: 'completed',
  chapter_count: 2,
  upvotes: 5,
  downvotes: 1,
  created_at: '2024-01-01T00:00:00',
  owner_name: 'testuser',
}

const mockWorld: WorldResponse = {
  id: 1,
  name: 'Winnie the Pooh',
  description: 'The Hundred Acre Wood — a cozy world with Pooh and friends.',
  is_builtin: true,
  visibility: 'public',
  prompt_template: 'Write a story about {language} and {theme} with {plot} in {num_chapters} chapters.',
  characters: { NARRATOR: 'Tells the story', WINNIE: 'A lovable bear who adores honey' },
  valid_speakers: ['NARRATOR', 'WINNIE'],
  voice_config: { NARRATOR: { voice_id: 'abc123', stability: 0.6 } },
  story_count: 5,
  owner_name: null,
  share_code: null,
  created_at: '2024-01-01T00:00:00',
  updated_at: '2024-01-01T00:00:00',
}

export const handlers = [
  // Auth
  http.get(`${BASE}/auth/me`, ({ request }) => {
    const auth = request.headers.get('Authorization')
    if (!auth || !auth.startsWith('Bearer ')) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 })
    }
    return HttpResponse.json(mockUser)
  }),

  http.post(`${BASE}/auth/login`, async () => {
    return HttpResponse.json({
      access_token: 'mock-token-123',
      token_type: 'bearer',
    } satisfies LoginResponse)
  }),

  http.post(`${BASE}/auth/register`, async () => {
    return HttpResponse.json(mockUser)
  }),

  http.get(`${BASE}/auth/api-keys`, () => {
    return HttpResponse.json(mockApiKeysStatus)
  }),

  http.put(`${BASE}/auth/api-keys`, async () => {
    return HttpResponse.json({
      ...mockApiKeysStatus,
      has_openai_key: true,
    } satisfies ApiKeysStatus)
  }),

  // Stories
  http.get(`${BASE}/stories/`, () => {
    return HttpResponse.json([mockStory])
  }),

  http.post(`${BASE}/stories/`, async () => {
    return HttpResponse.json({
      id: 2,
      title: 'New Story',
      description: null,
      prompt: null,
      language: null,
      world_id: null,
      world_name: null,
      status: 'created',
      visibility: 'private',
      share_code: null,
      upvotes: 0,
      downvotes: 0,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
      chapters: [],
      active_task: null,
    } satisfies StoryResponse)
  }),

  // Public
  http.get(`${BASE}/public/budget`, () => {
    return HttpResponse.json(mockBudget)
  }),

  http.get(`${BASE}/public/stories`, () => {
    return HttpResponse.json([mockStory])
  }),

  // Worlds
  http.get(`${BASE}/worlds/`, () => {
    return HttpResponse.json([mockWorld])
  }),

  http.get(`${BASE}/worlds/:id`, ({ params }) => {
    return HttpResponse.json({ ...mockWorld, id: Number(params['id']) })
  }),

  http.post(`${BASE}/worlds/`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      ...mockWorld,
      id: 2,
      name: body['name'] as string,
      description: (body['description'] as string) ?? null,
      is_builtin: false,
      visibility: (body['visibility'] as string) || 'private',
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    }, { status: 201 })
  }),

  // Bookmarks
  http.post(`${BASE}/bookmarks/stories/:id`, () => {
    return HttpResponse.json({ bookmarked: true })
  }),

  http.get(`${BASE}/bookmarks/stories`, () => {
    return HttpResponse.json([
      {
        id: 1,
        title: 'Bookmarked Story',
        description: 'A bookmarked story',
        language: 'Persian (Farsi)',
        status: 'completed',
        chapter_count: 2,
        upvotes: 5,
        downvotes: 1,
        created_at: '2024-01-01T00:00:00',
        owner_name: 'otheruser',
        bookmarked_at: '2024-06-01T00:00:00',
      } satisfies BookmarkedStoryListItem,
    ])
  }),

  // Fork
  http.post(`${BASE}/public/stories/:id/fork`, () => {
    return HttpResponse.json({
      id: 99,
      title: `Copy of ${mockStory.title}`,
      description: mockStory.description,
      prompt: null,
      language: mockStory.language,
      world_id: null,
      world_name: null,
      status: 'completed',
      visibility: 'private',
      share_code: null,
      upvotes: 0,
      downvotes: 0,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
      chapters: [],
      active_task: null,
    } satisfies StoryResponse, { status: 201 })
  }),

  // Voice config
  http.get(`${BASE}/stories/:storyId/voice-config`, () => {
    return HttpResponse.json({
      speakers: ['NARRATOR', 'WINNIE'],
      voice_config: {
        NARRATOR: { voice_id: 'abc123', stability: 0.6 },
        WINNIE: { voice_id: 'def456', stability: 0.5 },
      },
    } satisfies VoiceConfigResponse)
  }),

  // Voices list
  http.get(`${BASE}/stories/voices`, () => {
    return HttpResponse.json([
      { voice_id: 'abc123', name: 'Alice', category: 'premade', labels: {}, preview_url: '' },
      { voice_id: 'def456', name: 'Bob', category: 'premade', labels: {}, preview_url: '' },
      { voice_id: 'ghi789', name: 'Charlie', category: 'premade', labels: {}, preview_url: '' },
    ] satisfies VoiceListItem[])
  }),

  // Task
  http.get(`${BASE}/stories/tasks/:taskId`, ({ params }) => {
    return HttpResponse.json({
      task_id: params['taskId'] as string,
      status: 'running',
      progress: 50,
      message: 'Generating chapter 1...',
      result: null,
      words_generated: null,
      estimated_total_words: null,
    } satisfies TaskStatusResponse)
  }),

  http.delete(`${BASE}/stories/tasks/:taskId`, ({ params }) => {
    return HttpResponse.json({
      message: 'Task cancelled',
      task_id: params['taskId'],
    })
  }),
]

export { mockUser, mockApiKeysStatus, mockBudget, mockStory, mockWorld }
