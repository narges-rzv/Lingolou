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

export { mockUser, mockApiKeysStatus, mockBudget, mockStory }
