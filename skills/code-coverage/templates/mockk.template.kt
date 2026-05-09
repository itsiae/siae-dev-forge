/**
 * Use this template for: Kotlin (Spring Boot, Ktor, Android).
 * Requires: JUnit 5, MockK 1.13+, kotlinx-coroutines-test, AssertJ or kotlin.test.
 * Replace all {{PLACEHOLDER}} tokens before use.
 */

package {{package_name}}

import io.mockk.*
import io.mockk.impl.annotations.InjectMockKs
import io.mockk.impl.annotations.MockK
import kotlinx.coroutines.test.runTest
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.*
import org.junit.jupiter.api.extension.ExtendWith

import {{full_class_import}}
import {{full_dep_import}}

@ExtendWith(MockKExtension::class)
@DisplayName("{{ClassName}} unit tests")
class {{ClassName}}Test {

    @MockK
    lateinit var {{depName}}: {{DepInterface}}

    @InjectMockKs
    lateinit var {{instanceName}}: {{ClassName}}

    @BeforeEach
    fun setUp() {
        clearAllMocks()
    }

    @AfterEach
    fun tearDown() {
        unmockkAll()
    }

    // ─── Happy Path ───────────────────────────────────────────────────────────

    @Test
    @DisplayName("should {{HAPPY_PATH_DESCRIPTION}}")
    fun `should {{happy path description}}`() {
        // Arrange
        val input = {{HAPPY_PATH_INPUT}}
        val expected = {{EXPECTED_OUTPUT}}
        every { {{depName}}.{{depMethod}}(any()) } returns {{DEP_RETURN_VALUE}}

        // Act
        val result = {{instanceName}}.{{methodName}}(input)

        // Assert
        assertThat(result).isEqualTo(expected)
        verify(exactly = 1) { {{depName}}.{{depMethod}}(input) }
        confirmVerified({{depName}})
    }

    // ─── Edge Cases ───────────────────────────────────────────────────────────

    @Test
    @DisplayName("should {{EDGE_CASE_1_DESCRIPTION}} when input is empty")
    fun `should handle empty input`() {
        // Arrange
        every { {{depName}}.{{depMethod}}(any()) } returns {{EDGE_CASE_1_DEP_RETURN}}

        // Act
        val result = {{instanceName}}.{{methodName}}({{EDGE_CASE_1_INPUT}})

        // Assert
        assertThat(result).isEqualTo({{EDGE_CASE_1_EXPECTED}})
    }

    @Test
    @DisplayName("should {{EDGE_CASE_2_DESCRIPTION}} at boundary")
    fun `should handle boundary value`() {
        // Arrange
        val boundaryInput = {{EDGE_CASE_2_INPUT}}
        every { {{depName}}.{{depMethod}}(any()) } returns {{EDGE_CASE_2_DEP_RETURN}}

        // Act
        val result = {{instanceName}}.{{methodName}}(boundaryInput)

        // Assert
        assertThat(result).isNotNull
    }

    // ─── Negative Path ────────────────────────────────────────────────────────

    @Test
    @DisplayName("should throw {{ExceptionType}} when {{NEGATIVE_CONDITION}}")
    fun `should throw when input is invalid`() {
        // Arrange
        every { {{depName}}.{{depMethod}}(any()) } throws {{ExceptionType}}("{{ERROR_MESSAGE}}")

        // Act & Assert
        assertThatThrownBy { {{instanceName}}.{{methodName}}({{INVALID_INPUT}}) }
            .isInstanceOf({{ExceptionType}}::class.java)
            .hasMessageContaining("{{ERROR_MESSAGE}}")
    }

    // ─── Coroutine (suspend function) tests ───────────────────────────────────

    @Test
    @DisplayName("should {{SUSPEND_HAPPY_PATH_DESCRIPTION}} (suspend)")
    fun `should handle async operation`() = runTest {
        // Arrange
        coEvery { {{depName}}.{{suspendDepMethod}}(any()) } returns {{DEP_RETURN_VALUE}}

        // Act
        val result = {{instanceName}}.{{suspendMethodName}}({{HAPPY_PATH_INPUT}})

        // Assert
        assertThat(result).isEqualTo({{EXPECTED_OUTPUT}})
        coVerify(exactly = 1) { {{depName}}.{{suspendDepMethod}}(any()) }
    }

    @Test
    @DisplayName("should propagate exception from suspend dep")
    fun `should propagate coroutine exception`() = runTest {
        // Arrange
        coEvery { {{depName}}.{{suspendDepMethod}}(any()) } throws {{ExceptionType}}("{{ERROR_MESSAGE}}")

        // Act & Assert
        assertThrows<{{ExceptionType}}> {
            {{instanceName}}.{{suspendMethodName}}({{HAPPY_PATH_INPUT}})
        }
    }
}
