import { describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('./http', () => api)

import { buildImageUrl, listAssetHistoryPage } from './platform'

describe('buildImageUrl', () => {
  it('routes checked images to the dedicated image-check static path', () => {
    expect(buildImageUrl('model/image_check/19_0_1639449177.png')).toBe('/files/image-checks/19_0_1639449177.png')
  })

  it('keeps generated images on the default image path', () => {
    expect(buildImageUrl('model/image/19_0_1639449177.png')).toBe('/files/images/19_0_1639449177.png')
  })
})

describe('listAssetHistoryPage', () => {
  it('requests the paged history endpoint with backend query params', async () => {
    api.http.get.mockResolvedValue({
      data: {
        data: {
          items: [],
          page: 2,
          page_size: 20,
          total: 42,
          total_pages: 3,
        },
      },
    })

    await listAssetHistoryPage({
      page: 2,
      page_size: 20,
      prompt_keyword: 'tower',
      model_name: 'ssd1b-electric',
      status: 'scored',
      min_total_score: 60,
    })

    expect(api.http.get).toHaveBeenCalledWith('/assets/history/page', {
      params: {
        page: 2,
        page_size: 20,
        prompt_keyword: 'tower',
        model_name: 'ssd1b-electric',
        status: 'scored',
        min_total_score: 60,
      },
    })
  })
})
