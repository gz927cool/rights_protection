import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useCase } from '../hooks/useCase'

export function Home() {
  const navigate = useNavigate()
  const { createCase, isCreating } = useCase()

  const handleStart = async () => {
    await createCase()
    navigate('/case')
  }

  return (
    <div className="home">
      <h1>工会劳动维权 AI 引导系统</h1>
      <p>帮助您通过结构化引导完成劳动维权</p>
      <button onClick={handleStart} disabled={isCreating}>
        {isCreating ? '创建中...' : '开始维权'}
      </button>
    </div>
  )
}
