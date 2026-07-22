/** web-vitals 工具函数测试 */

import { describe, it, expect } from 'vitest'
import { getMetricRating } from './web-vitals'

describe('getMetricRating', () => {
  describe('LCP (Largest Contentful Paint)', () => {
    it('returns good for LCP <= 2500ms', () => {
      expect(getMetricRating('LCP', 0)).toBe('good')
      expect(getMetricRating('LCP', 1000)).toBe('good')
      expect(getMetricRating('LCP', 2500)).toBe('good')
    })

    it('returns needs-improvement for 2500ms < LCP <= 4000ms', () => {
      expect(getMetricRating('LCP', 2501)).toBe('needs-improvement')
      expect(getMetricRating('LCP', 3000)).toBe('needs-improvement')
      expect(getMetricRating('LCP', 4000)).toBe('needs-improvement')
    })

    it('returns poor for LCP > 4000ms', () => {
      expect(getMetricRating('LCP', 4001)).toBe('poor')
      expect(getMetricRating('LCP', 10000)).toBe('poor')
    })
  })

  describe('INP (Interaction to Next Paint)', () => {
    it('returns good for INP <= 200ms', () => {
      expect(getMetricRating('INP', 0)).toBe('good')
      expect(getMetricRating('INP', 100)).toBe('good')
      expect(getMetricRating('INP', 200)).toBe('good')
    })

    it('returns needs-improvement for 200ms < INP <= 500ms', () => {
      expect(getMetricRating('INP', 201)).toBe('needs-improvement')
      expect(getMetricRating('INP', 350)).toBe('needs-improvement')
      expect(getMetricRating('INP', 500)).toBe('needs-improvement')
    })

    it('returns poor for INP > 500ms', () => {
      expect(getMetricRating('INP', 501)).toBe('poor')
      expect(getMetricRating('INP', 1000)).toBe('poor')
    })
  })

  describe('CLS (Cumulative Layout Shift)', () => {
    it('returns good for CLS <= 0.1', () => {
      expect(getMetricRating('CLS', 0)).toBe('good')
      expect(getMetricRating('CLS', 0.05)).toBe('good')
      expect(getMetricRating('CLS', 0.1)).toBe('good')
    })

    it('returns needs-improvement for 0.1 < CLS <= 0.25', () => {
      expect(getMetricRating('CLS', 0.11)).toBe('needs-improvement')
      expect(getMetricRating('CLS', 0.2)).toBe('needs-improvement')
      expect(getMetricRating('CLS', 0.25)).toBe('needs-improvement')
    })

    it('returns poor for CLS > 0.25', () => {
      expect(getMetricRating('CLS', 0.26)).toBe('poor')
      expect(getMetricRating('CLS', 1)).toBe('poor')
    })
  })

  describe('FCP (First Contentful Paint)', () => {
    it('returns good for FCP <= 1800ms', () => {
      expect(getMetricRating('FCP', 0)).toBe('good')
      expect(getMetricRating('FCP', 1000)).toBe('good')
      expect(getMetricRating('FCP', 1800)).toBe('good')
    })

    it('returns needs-improvement for 1800ms < FCP <= 3000ms', () => {
      expect(getMetricRating('FCP', 1801)).toBe('needs-improvement')
      expect(getMetricRating('FCP', 2500)).toBe('needs-improvement')
      expect(getMetricRating('FCP', 3000)).toBe('needs-improvement')
    })

    it('returns poor for FCP > 3000ms', () => {
      expect(getMetricRating('FCP', 3001)).toBe('poor')
      expect(getMetricRating('FCP', 5000)).toBe('poor')
    })
  })

  describe('TTFB (Time to First Byte)', () => {
    it('returns good for TTFB <= 800ms', () => {
      expect(getMetricRating('TTFB', 0)).toBe('good')
      expect(getMetricRating('TTFB', 500)).toBe('good')
      expect(getMetricRating('TTFB', 800)).toBe('good')
    })

    it('returns needs-improvement for 800ms < TTFB <= 1800ms', () => {
      expect(getMetricRating('TTFB', 801)).toBe('needs-improvement')
      expect(getMetricRating('TTFB', 1000)).toBe('needs-improvement')
      expect(getMetricRating('TTFB', 1800)).toBe('needs-improvement')
    })

    it('returns poor for TTFB > 1800ms', () => {
      expect(getMetricRating('TTFB', 1801)).toBe('poor')
      expect(getMetricRating('TTFB', 5000)).toBe('poor')
    })
  })

  describe('unknown metric', () => {
    it('returns good for unknown metric with value 0', () => {
      // 未知指标的阈值默认为 [0, 0]，所以 0 被视为 good
      expect(getMetricRating('UNKNOWN', 0)).toBe('good')
    })

    it('returns poor for unknown metric with positive value', () => {
      // 未知指标的阈值默认为 [0, 0]，任何 > 0 的值都是 poor
      expect(getMetricRating('UNKNOWN', 0.5)).toBe('poor')
      expect(getMetricRating('UNKNOWN', 100)).toBe('poor')
    })
  })
})
