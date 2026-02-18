import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:5173/api'

const mockUser = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  is_active: true,
  created_at: '2024-01-01T00:00:00',
}

const mockApiKeysStatus = {
  has_openai_key: false,
  has_elevenlabs_key: false,
  free_stories_used: 0,
  free_stories_limit: 3,
}

const mockBudget = {
  total_budget: 50.0,
  total_spent: 5.0,
  free_stories_generated: 10,
  free_stories_per_user: 3,
}

const mockStory = {
  id: 1,
  title: 'Test Story',
  description: 'A test story',
  language: 'Persian (Farsi)',
  status: 'completed',
  visibility: 'public',
  chapter_count: 2,
  upvotes: 5,
  downvotes: 1,
  created_at: '2024-01-01T00:00:00',
  owner_name: 'testuser',
}

const mockWorld = {
  id: 1,
  name: 'PAW Patrol',
  description: 'The classic PAW Patrol language learning world.',
  is_builtin: true,
  visibility: 'public',
  prompt_template: 'Write a story about {language} and {theme} with {plot} in {num_chapters} chapters.',
  characters: { NARRATOR: 'Tells the story', RYDER: 'The human leader' },
  valid_speakers: ['NARRATOR', 'RYDER'],
  voice_config: { NARRATOR: { voice_id: 'abc123', stability: 0.6 } },
  story_count: 5,
  owner_name: null,
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
    })
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
    })
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
      status: 'created',
      visibility: 'private',
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
      chapters: [],
    })
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
    return HttpResponse.json({ ...mockWorld, id: Number(params.id) })
  }),

  http.post(`${BASE}/worlds/`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      ...mockWorld,
      id: 2,
      name: body.name,
      description: body.description,
      is_builtin: false,
      visibility: body.visibility || 'private',
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
      },
    ])
  }),

  // Fork
  http.post(`${BASE}/public/stories/:id/fork`, ({ params }) => {
    return HttpResponse.json({
      id: 99,
      title: `Copy of ${mockStory.title}`,
      description: mockStory.description,
      prompt: null,
      language: mockStory.language,
      status: 'completed',
      visibility: 'private',
      share_code: null,
      upvotes: 0,
      downvotes: 0,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
      chapters: [],
    }, { status: 201 })
  }),

  // Voice config
  http.get(`${BASE}/stories/:storyId/voice-config`, () => {
    return HttpResponse.json({
      speakers: ['NARRATOR', 'RYDER'],
      voice_config: {
        NARRATOR: { voice_id: 'abc123', stability: 0.6 },
        RYDER: { voice_id: 'def456', stability: 0.5 },
      },
    })
  }),

  // Voices list
  http.get(`${BASE}/stories/voices`, () => {
    return HttpResponse.json([
      { voice_id: 'abc123', name: 'Alice', category: 'premade', labels: {}, preview_url: '' },
      { voice_id: 'def456', name: 'Bob', category: 'premade', labels: {}, preview_url: '' },
      { voice_id: 'ghi789', name: 'Charlie', category: 'premade', labels: {}, preview_url: '' },
    ])
  }),

  // Task
  http.get(`${BASE}/stories/tasks/:taskId`, ({ params }) => {
    return HttpResponse.json({
      task_id: params.taskId,
      status: 'running',
      progress: 50,
      message: 'Generating chapter 1...',
    })
  }),

  http.delete(`${BASE}/stories/tasks/:taskId`, ({ params }) => {
    return HttpResponse.json({
      message: 'Task cancelled',
      task_id: params.taskId,
    })
  }),
]

export { mockUser, mockApiKeysStatus, mockBudget, mockStory, mockWorld }
