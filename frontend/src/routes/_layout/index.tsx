import { Box, Container, HStack, Link, Text } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { createFileRoute } from "@tanstack/react-router"

import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <>
      <Container maxW="full">
        <Box pt={12} m={4}>
          <Text fontSize="2xl" truncate maxW="sm">
            Hi, {currentUser?.full_name || currentUser?.email} 👋🏼
          </Text>
          <Text>Welcome back, nice to see you again!</Text>
          <HStack mt={6} gap={4}>
            <RouterLink to="/docs">
              <Link color="teal.500">Open API Docs</Link>
            </RouterLink>
            <RouterLink to="/scraper">
              <Link color="teal.500">Open Scraper</Link>
            </RouterLink>
          </HStack>
        </Box>
      </Container>
    </>
  )
}
