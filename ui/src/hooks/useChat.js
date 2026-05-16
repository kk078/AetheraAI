import { useState, useCallback, useRef } from 'react';
import { api } from '../utils/api';

export function useChat(options = {}) {
  const {
    initialMessages = [],
    onMessage,
    onError,
    specialist,
  } = options;

  const [messages, setMessages] = useState(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);
  const messagesRef = useRef(initialMessages);

  // Keep ref in sync with state
  messagesRef.current = messages;

  const sendMessage = useCallback(async (content, additionalOptions = {}) => {
    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...messagesRef.current, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);
    setError(null);

    try {
      abortControllerRef.current = new AbortController();

      const stream = api.streamChat(content, {
        specialist: additionalOptions.specialist || specialist,
        model: additionalOptions.model,
        stream: true,
        signal: abortControllerRef.current.signal,
      });

      const assistantMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        specialist: additionalOptions.specialist || specialist || 'general',
        timestamp: new Date().toISOString(),
        model: undefined,
        confidence: undefined,
        reasoningChain: undefined,
        toolCalls: undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      for await (const chunk of stream) {
        if (chunk.type === 'content') {
          assistantMessage.content += chunk.data;
        } else if (chunk.type === 'metadata') {
          if (chunk.data.specialist) {
            assistantMessage.specialist = chunk.data.specialist;
          }
          if (chunk.data.model) {
            assistantMessage.model = chunk.data.model;
          }
          if (chunk.data.confidence !== undefined) {
            assistantMessage.confidence = chunk.data.confidence;
          }
          if (chunk.data.reasoning_chain) {
            assistantMessage.reasoningChain = chunk.data.reasoning_chain;
          }
          if (chunk.data.tool_calls) {
            assistantMessage.toolCalls = chunk.data.tool_calls;
          }
        } else if (chunk.type === 'error') {
          throw new Error(chunk.data);
        }

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...assistantMessage };
          return updated;
        });

        onMessage?.(assistantMessage);
      }

      return assistantMessage;
    } catch (err) {
      if (err.name === 'AbortError') return;

      const errorMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: ${err.message}`,
        specialist: 'general',
        timestamp: new Date().toISOString(),
        isError: true,
      };

      setMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.findIndex(
          (m, i) => i === updated.length - 1 && m.role === 'assistant' && !m.content
        );
        if (lastIdx !== -1) {
          updated[lastIdx] = errorMessage;
        } else {
          updated.push(errorMessage);
        }
        return updated;
      });

      setError(err.message);
      onError?.(err);
      throw err;
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [specialist, onMessage, onError]);

  const loadConversation = useCallback(async (conversationId) => {
    try {
      const data = await api.getConversation(conversationId);
      const loadedMessages = (data.messages || []).map((msg) => ({
        id: msg.id || crypto.randomUUID(),
        role: msg.role,
        content: msg.content,
        specialist: msg.specialist || 'general',
        model: msg.model,
        confidence: msg.confidence,
        timestamp: msg.timestamp || new Date().toISOString(),
        reasoningChain: msg.reasoning_chain,
        toolCalls: msg.tool_calls,
      }));
      setMessages(loadedMessages);
      return loadedMessages;
    } catch (err) {
      setError(err.message);
      return [];
    }
  }, []);

  const stopGeneration = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsLoading(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  const retry = useCallback(async () => {
    const lastUserMessage = messagesRef.current.filter((m) => m.role === 'user').pop();
    if (lastUserMessage) {
      await sendMessage(lastUserMessage.content);
    }
  }, [sendMessage]);

  return {
    messages,
    setMessages,
    isLoading,
    error,
    sendMessage,
    loadConversation,
    stopGeneration,
    clearMessages,
    retry,
  };
}

export default useChat;