import React from "react"

import { Box, Button, Container, HStack, Heading, Input, Stack, Text, Textarea } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

import { OpenAPI } from "@/client/core/OpenAPI"

export const Route = createFileRoute("/playground")({
  component: Playground,
})

function resolveBaseUrl() {
  const base = (OpenAPI.BASE || "").replace(/\/$/, "")
  if (base) return base
  // Fallback: assume same origin
  return ""
}

function SectionDivider() {
  return <Box borderTop="1px" borderColor="gray.200" my={4} />
}

function Playground() {
  const [baseUrl, setBaseUrl] = React.useState<string>(resolveBaseUrl())
  const [email, setEmail] = React.useState<string>("")
  const [password, setPassword] = React.useState<string>("")
  const [token, setToken] = React.useState<string>("")
  const [companies, setCompanies] = React.useState<string>("laudite, laudos.ai, leorad")
  const [runResult, setRunResult] = React.useState<string>("")
  const [postsResult, setPostsResult] = React.useState<string>("")
  const [companyFilter, setCompanyFilter] = React.useState<string>("")

  // Examples state
  const [pmQuery, setPmQuery] = React.useState<string>("radiology AI")
  const [pmSearchOut, setPmSearchOut] = React.useState<string>("")
  const [pmid, setPmid] = React.useState<string>("")
  const [pmSummary, setPmSummary] = React.useState<string>("")
  const [askQ, setAskQ] = React.useState<string>("What are current approaches to AI radiology report generation?")
  const [askUrls, setAskUrls] = React.useState<string>("https://laudite.com.br, https://laudos.ai")
  const [askAnswer, setAskAnswer] = React.useState<string>("")

  const api = (path: string) => `${baseUrl}${path}`

  async function login() {
    try {
      const body = new URLSearchParams()
      body.set("username", email)
      body.set("password", password)
      const res = await fetch(api("/api/v1/login/access-token"), {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      })
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
      const data = await res.json()
      const t = data.access_token as string
      setToken(t)
    } catch (e: any) {
      setToken("")
      alert(`Login failed: ${e?.message || e}`)
    }
  }

  async function runScraper() {
    try {
      const url = new URL(api("/api/v1/scraper/run/"))
      for (const c of companies.split(",").map((s) => s.trim()).filter(Boolean)) {
        url.searchParams.append("companies", c)
      }
      const res = await fetch(url.toString(), {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        credentials: "include",
      })
      const text = await res.text()
      setRunResult(text)
      if (!res.ok) throw new Error(`${res.status} ${text}`)
    } catch (e: any) {
      alert(`Run failed: ${e?.message || e}`)
    }
  }

  async function listPosts() {
    try {
      const url = new URL(api("/api/v1/scraper/posts/"))
      if (companyFilter) url.searchParams.set("company", companyFilter)
      const res = await fetch(url.toString(), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        credentials: "include",
      })
      const text = await res.text()
      setPostsResult(text)
      if (!res.ok) throw new Error(`${res.status} ${text}`)
    } catch (e: any) {
      alert(`List failed: ${e?.message || e}`)
    }
  }

  // Examples
  async function pubmedSearch() {
    try {
      const res = await fetch(api("/api/v1/examples/pubmed/search"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: pmQuery, max_results: 10 }),
      })
      const text = await res.text()
      setPmSearchOut(text)
      if (res.ok) {
        try {
          const data = JSON.parse(text)
          setPmid(data?.items?.[0]?.pmid || "")
        } catch {}
      }
      if (!res.ok) throw new Error(`${res.status} ${text}`)
    } catch (e: any) {
      alert(`PubMed search failed: ${e?.message || e}`)
    }
  }

  async function pubmedSummarize() {
    try {
      const res = await fetch(api("/api/v1/examples/pubmed/summarize"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pmid }),
      })
      const text = await res.text()
      setPmSummary(text)
      if (!res.ok) throw new Error(`${res.status} ${text}`)
    } catch (e: any) {
      alert(`Summarize failed: ${e?.message || e}`)
    }
  }

  async function askWithUrls() {
    try {
      const urls = askUrls.split(",").map((s) => s.trim()).filter(Boolean)
      const res = await fetch(api("/api/v1/examples/ask"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: askQ, urls }),
      })
      const text = await res.text()
      setAskAnswer(text)
      if (!res.ok) throw new Error(`${res.status} ${text}`)
    } catch (e: any) {
      alert(`Ask failed: ${e?.message || e}`)
    }
  }

  return (
    <Container maxW="container.lg" py={8}>
      <Stack gap={6}>
        <Heading size="lg">Scraper Playground</Heading>

        <Box>
          <Text fontWeight="bold" mb={2}>
            API Base URL
          </Text>
          <HStack gap={3} align="center">
            <Input placeholder="http://localhost:8000" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </HStack>
          <Text fontSize="sm" color="gray.500" mt={1}>
            Leave empty to use same origin. In Docker override, backend runs at http://localhost:8000
          </Text>
        </Box>

        <SectionDivider />

        <Box>
          <Text fontWeight="bold" mb={2}>
            Authenticate (Superuser)
          </Text>
          <HStack gap={3} align="center">
            <Input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Input placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <Button onClick={login}>Login</Button>
          </HStack>
          <Text fontSize="xs" color={token ? "green.500" : "gray.500"} mt={1}>
            {token ? `Token acquired (${token.slice(0, 12)}...)` : "No token yet"}
          </Text>
        </Box>

        <SectionDivider />

        <Box>
          <Text fontWeight="bold" mb={2}>
            Run Scraper
          </Text>
          <HStack gap={3}>
            <Input
              placeholder="companies (comma-separated)"
              value={companies}
              onChange={(e) => setCompanies(e.target.value)}
            />
            <Button onClick={runScraper}>Run</Button>
          </HStack>
          <Textarea value={runResult} onChange={() => {}} rows={8} mt={3} fontFamily="mono" />
        </Box>

        <SectionDivider />

        <Box>
          <Text fontWeight="bold" mb={2}>
            List Posts
          </Text>
          <HStack gap={3}>
            <Input placeholder="filter by company (optional)" value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)} />
            <Button onClick={listPosts}>Fetch</Button>
          </HStack>
          <Textarea value={postsResult} onChange={() => {}} rows={14} mt={3} fontFamily="mono" />
        </Box>

        <SectionDivider />

        <Heading size="md">Cookbooks</Heading>

        <Box>
          <Text fontWeight="bold" mb={2}>PubMed: Search</Text>
          <HStack gap={3}>
            <Input value={pmQuery} onChange={(e) => setPmQuery(e.target.value)} />
            <Button onClick={pubmedSearch}>Search</Button>
          </HStack>
          <Textarea value={pmSearchOut} onChange={() => {}} rows={8} mt={3} fontFamily="mono" />
        </Box>

        <Box>
          <Text fontWeight="bold" mb={2}>PubMed: Summarize (GPT-4o)</Text>
          <HStack gap={3}>
            <Input placeholder="pmid" value={pmid} onChange={(e) => setPmid(e.target.value)} />
            <Button onClick={pubmedSummarize}>Summarize</Button>
          </HStack>
          <Textarea value={pmSummary} onChange={() => {}} rows={8} mt={3} fontFamily="mono" />
          <Text fontSize="xs" color="gray.500">Requires OPENAI_API_KEY configured in backend.</Text>
        </Box>

        <Box>
          <Text fontWeight="bold" mb={2}>Ask with URLs (Perplexity-like)</Text>
          <Input placeholder="Question" value={askQ} onChange={(e) => setAskQ(e.target.value)} mb={2} />
          <Input placeholder="URLs (comma-separated)" value={askUrls} onChange={(e) => setAskUrls(e.target.value)} mb={2} />
          <Button onClick={askWithUrls}>Ask</Button>
          <Textarea value={askAnswer} onChange={() => {}} rows={10} mt={3} fontFamily="mono" />
        </Box>
      </Stack>
    </Container>
  )
}
